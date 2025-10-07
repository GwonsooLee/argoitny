"""Celery tasks for async processing - Optimized for performance"""
from celery import shared_task
from django.db import models, transaction
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from .models import ScriptGenerationJob, ProblemExtractionJob, Problem, TestCase, SearchHistory, User, JobProgressHistory
from .services.gemini_service import GeminiService
from .services.code_execution_service import CodeExecutionService
import base64
import re
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TASK CONFIGURATION CONSTANTS
# ============================================================================
TASK_DEFAULT_RETRY_DELAY = 60  # seconds
TASK_FAST_RETRY_DELAY = 10  # seconds for quick retries
TASK_DELETE_RETRY_DELAY = 30  # seconds for delete operations
MAX_RETRIES = 3
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour


# ============================================================================
# OPTIMIZED SCRIPT GENERATION TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1680,  # 28 minutes soft limit
    acks_late=True,  # Acknowledge after task completion
    reject_on_worker_lost=True,  # Reject task if worker crashes
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes backoff
    retry_jitter=True,  # Add randomness to backoff
)
def generate_script_task(self, job_id):
    """
    Async task to generate test case generator script using Gemini AI

    OPTIMIZATIONS:
    - Use update_fields for targeted database updates
    - Atomic transactions for data consistency
    - Bulk operations for test case creation
    - Early exit on validation failures
    - Exception handling with proper logging

    Args:
        job_id: ID of the ScriptGenerationJob

    Returns:
        dict: Result with job_id and status
    """
    logger.info(f"[generate_script_task] Task started for job {job_id}")
    logger.info(f"[generate_script_task] Worker: {self.request.hostname}, Task ID: {self.request.id}")

    try:
        # OPTIMIZATION: Use transaction.atomic() with select_for_update to prevent race conditions
        with transaction.atomic():
            try:
                job = ScriptGenerationJob.objects.only(
                    'id', 'platform', 'problem_id', 'title', 'solution_code',
                    'language', 'constraints', 'tags', 'problem_url', 'status'
                ).select_for_update(skip_locked=True).get(id=job_id)
                logger.info(f"[generate_script_task] Job {job_id} loaded: {job.platform}/{job.problem_id} - {job.title}")
            except ScriptGenerationJob.DoesNotExist:
                logger.warning(f"[generate_script_task] Job {job_id} not found, may have been deleted")
                return {
                    'job_id': job_id,
                    'status': 'NOT_FOUND',
                    'message': 'Job not found in database'
                }

            # Skip if already processing (another worker grabbed it)
            if job.status == 'PROCESSING':
                logger.warning(f"[generate_script_task] Job {job_id} already processing, skipping")
                return {
                    'job_id': job_id,
                    'status': 'SKIPPED',
                    'message': 'Job already being processed'
                }

            # OPTIMIZATION: Update status to PROCESSING (use update_fields)
            logger.info(f"[generate_script_task] Updating job {job_id} status to PROCESSING")
            job.status = 'PROCESSING'
            job.celery_task_id = self.request.id
            job.save(update_fields=['status', 'celery_task_id'])

        # Prepare problem info for Gemini
        problem_info = {
            'platform': job.platform,
            'problem_id': job.problem_id,
            'title': job.title,
            'solution_code': job.solution_code or '',
            'language': job.language,
            'constraints': job.constraints,
            'tags': job.tags,
        }
        logger.info(f"[generate_script_task] Prepared problem info for job {job_id}")
        logger.info(f"[generate_script_task] Constraints: {job.constraints[:200]}...")

        # Check if there's a previous failure to learn from
        previous_failure = None
        if job.generator_code and job.error_message:
            # This is a retry - provide context about previous failure
            previous_failure = {
                'code': job.generator_code,
                'error': job.error_message
            }
            logger.info(f"[generate_script_task] Retry attempt with previous failure context")
            logger.info(f"[generate_script_task] Previous error: {job.error_message[:200]}...")

        # Generate script using Gemini
        logger.info(f"[generate_script_task] Calling Gemini API to generate test case generator...")
        gemini_service = GeminiService()
        generator_code = gemini_service.generate_test_case_generator_code(problem_info, previous_failure=previous_failure)
        logger.info(f"[generate_script_task] Gemini returned generator code ({len(generator_code)} chars)")

        # VALIDATION: Check for placeholder code
        if '"""' in generator_code or '"..."' in generator_code or "case_data = '...'" in generator_code:
            logger.error(f"[generate_script_task] Generated code contains placeholder strings!")
            raise ValueError("Generated code contains placeholder strings - Gemini did not generate actual test case logic")

        # OPTIMIZATION: Update job with result (use update_fields)
        logger.info(f"[generate_script_task] Updating job {job_id} status to COMPLETED")
        job.status = 'COMPLETED'
        job.generator_code = generator_code
        job.save(update_fields=['status', 'generator_code'])

        # Execute generator code to create test cases and save to Problem
        try:
            from .services.test_case_generator import TestCaseGenerator

            # Generate test cases using the script
            test_case_inputs = TestCaseGenerator.execute_generator_code(
                code=generator_code,
                num_cases=20
            )

            # OPTIMIZATION: Encode solution_code to base64 for consistency
            encoded_solution_code = ''
            if job.solution_code:
                encoded_solution_code = base64.b64encode(
                    job.solution_code.encode('utf-8')
                ).decode('utf-8')

            problem_defaults = {
                'title': job.title,
                'problem_url': job.problem_url or '',
                'tags': job.tags or [],
                'solution_code': encoded_solution_code,
                'language': job.language,
                'constraints': job.constraints
            }

            # OPTIMIZATION: Use update_or_create for atomic operation
            problem, created = Problem.objects.update_or_create(
                platform=job.platform,
                problem_id=job.problem_id,
                defaults=problem_defaults
            )

            # OPTIMIZATION: Use atomic transaction for test case operations
            with transaction.atomic():
                # Delete existing test cases in bulk
                deleted_count = TestCase.objects.filter(problem=problem).delete()[0]
                logger.info(f"Deleted {deleted_count} existing test cases for problem {problem.id}")

                # Execute solution code with generated inputs to get outputs
                if job.solution_code:
                    test_results = CodeExecutionService.execute_with_test_cases(
                        code=job.solution_code,
                        language=job.language,
                        test_inputs=test_case_inputs
                    )

                    # Log execution results
                    success_count = sum(1 for r in test_results if r['status'] == 'success')
                    failed_count = len(test_results) - success_count
                    logger.info(
                        f"[generate_script_task] Test case execution: "
                        f"{success_count} succeeded, {failed_count} failed"
                    )

                    # Log failed test cases (only first 3 to avoid log spam)
                    for idx, r in enumerate(r for r in test_results if r['status'] != 'success'):
                        if idx >= 3:  # Limit to first 3 failures
                            break
                        logger.warning(
                            f"[generate_script_task] Failed test case {idx+1}: "
                            f"input={r.get('input', '')[:50]}, error={r.get('error', 'Unknown')}"
                        )

                    # OPTIMIZATION: Bulk create test cases with successful results only
                    test_case_objects = [
                        TestCase(
                            problem=problem,
                            input=r['input'],
                            output=r['output']
                        )
                        for r in test_results if r['status'] == 'success'
                    ]

                    if test_case_objects:
                        TestCase.objects.bulk_create(
                            test_case_objects,
                            batch_size=100  # Process in batches for memory efficiency
                        )
                        logger.info(f"Created {len(test_case_objects)} test cases for problem {problem.id}")
                        logger.info(f"Problem {problem.id} remains in draft state - admin review required")
                    else:
                        logger.warning(f"No successful test cases generated for problem {problem.id}")
                else:
                    # No solution code, create test cases with empty outputs
                    test_case_objects = [
                        TestCase(
                            problem=problem,
                            input=test_input,
                            output=''
                        )
                        for test_input in test_case_inputs
                    ]

                    if test_case_objects:
                        TestCase.objects.bulk_create(
                            test_case_objects,
                            batch_size=100
                        )
                        logger.info(f"Created {len(test_case_objects)} test cases (no outputs) for problem {problem.id}")
                        logger.info(f"Problem {problem.id} remains in draft state - admin review required")

        except Exception as e:
            # Log but don't fail the task if test case generation fails
            logger.error(f"Failed to generate/save test cases for job {job_id}: {str(e)}", exc_info=True)

        return {
            'job_id': job_id,
            'status': 'COMPLETED',
            'message': 'Script generated successfully'
        }

    except ScriptGenerationJob.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return {
            'job_id': job_id,
            'status': 'FAILED',
            'error': 'Job not found'
        }

    except Exception as e:
        logger.error(f"Error in generate_script_task for job {job_id}: {str(e)}", exc_info=True)

        # OPTIMIZATION: Update job with error using only() + update_fields
        try:
            job = ScriptGenerationJob.objects.only('id', 'status', 'error_message').get(id=job_id)
            job.status = 'FAILED'
            job.error_message = str(e)
            job.save(update_fields=['status', 'error_message'])
        except Exception as update_error:
            logger.error(f"Failed to update job status: {str(update_error)}")

        # Don't retry - handled by autoretry_for
        raise


# ============================================================================
# OPTIMIZED OUTPUT GENERATION TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=900,  # 15 minutes hard limit
    soft_time_limit=840,  # 14 minutes soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_outputs_task(self, platform, problem_id):
    """
    Async task to generate outputs for test cases using solution code

    OPTIMIZATIONS:
    - Prefetch test_cases to avoid N+1 queries
    - Use only() to fetch minimal fields
    - Bulk update instead of individual saves
    - Atomic transaction for consistency
    - Efficient list comprehensions

    Args:
        platform: Platform name (e.g., 'baekjoon', 'codeforces')
        problem_id: Problem ID

    Returns:
        dict: Result with status and count
    """
    try:
        # OPTIMIZATION: Use only() + prefetch_related to minimize queries
        problem = Problem.objects.only(
            'id', 'solution_code', 'language', 'platform', 'problem_id'
        ).prefetch_related(
            models.Prefetch(
                'test_cases',
                queryset=TestCase.objects.only('id', 'input', 'output', 'problem_id')
            )
        ).get(
            platform=platform,
            problem_id=problem_id
        )

        # Early validation
        if not problem.solution_code:
            logger.warning(f"Problem {platform}/{problem_id} has no solution code")
            return {
                'status': 'FAILED',
                'error': 'Problem has no solution code'
            }

        # OPTIMIZATION: Get test cases from prefetch (no additional query)
        test_cases = list(problem.test_cases.all())
        if not test_cases:
            logger.warning(f"Problem {platform}/{problem_id} has no test cases")
            return {
                'status': 'FAILED',
                'error': 'Problem has no test cases'
            }

        # OPTIMIZATION: Extract inputs in single list comprehension
        test_inputs = [tc.input for tc in test_cases]

        # Decode base64 solution code before executing
        try:
            decoded_code = base64.b64decode(problem.solution_code).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decode solution code: {str(e)}")
            return {
                'status': 'FAILED',
                'error': f'Failed to decode solution code: {str(e)}'
            }

        # Execute solution code with test inputs
        test_results = CodeExecutionService.execute_with_test_cases(
            code=decoded_code,
            language=problem.language or 'python',
            test_inputs=test_inputs
        )

        # OPTIMIZATION: Use bulk_update in atomic transaction
        with transaction.atomic():
            test_cases_to_update = []
            failed_cases = []

            for tc, result in zip(test_cases, test_results):
                if result['status'] == 'success':
                    tc.output = result['output']
                    test_cases_to_update.append(tc)
                else:
                    failed_cases.append({
                        'input': result.get('input', '')[:50],
                        'error': result.get('error', 'Unknown error')
                    })

            # Bulk update all successful test cases at once (single query)
            if test_cases_to_update:
                TestCase.objects.bulk_update(
                    test_cases_to_update,
                    ['output'],
                    batch_size=100  # Process in batches
                )

        # Calculate summary
        success_count = len(test_cases_to_update)
        failed_count = len(failed_cases)

        # Log summary and failures
        logger.info(
            f"Output generation for {platform}/{problem_id}: "
            f"{success_count} succeeded, {failed_count} failed out of {len(test_results)} total"
        )

        # Log first few failures only
        for idx, failed_case in enumerate(failed_cases[:3]):
            logger.warning(
                f"Failed test case {idx+1}: input={failed_case['input']}, "
                f"error={failed_case['error']}"
            )

        return {
            'status': 'COMPLETED',
            'count': success_count,
            'failed_count': failed_count,
            'message': f'Outputs generated successfully for {success_count} test cases'
        }

    except Problem.DoesNotExist:
        logger.error(f"Problem {platform}/{problem_id} not found")
        return {
            'status': 'FAILED',
            'error': 'Problem not found'
        }

    except Exception as e:
        logger.error(
            f"Error in generate_outputs_task for {platform}/{problem_id}: {str(e)}",
            exc_info=True
        )
        # Don't retry - handled by autoretry_for
        raise


# ============================================================================
# OPTIMIZED CODE EXECUTION TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=300,  # 5 minutes hard limit
    soft_time_limit=270,  # 4.5 minutes soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def execute_code_task(self, code, language, problem_id, user_id, user_identifier, is_code_public):
    """
    Async task to execute code against test cases

    OPTIMIZATIONS:
    - Use only() to fetch minimal problem fields
    - Prefetch test_cases to avoid N+1 queries
    - Use select_related for user lookup
    - Optimize metadata update with F() expression consideration
    - Efficient list comprehensions for result building
    - Single transaction for history creation

    Args:
        code: User's code
        language: Programming language
        problem_id: Problem ID
        user_id: User ID (if authenticated)
        user_identifier: User email or identifier
        is_code_public: Whether to make code public

    Returns:
        dict: Execution results
    """
    try:
        # OPTIMIZATION: Use only() + prefetch_related to minimize queries
        problem = Problem.objects.only(
            'id', 'platform', 'problem_id', 'title', 'metadata'
        ).prefetch_related(
            models.Prefetch(
                'test_cases',
                queryset=TestCase.objects.only('id', 'input', 'output', 'problem_id')
            )
        ).get(id=problem_id)

        # Early validation
        if not problem.test_cases.exists():
            logger.warning(f"Problem {problem_id} has no test cases")
            return {
                'status': 'FAILED',
                'error': 'No test cases available for this problem'
            }

        # OPTIMIZATION: Get test cases from prefetch (no additional query)
        test_cases = list(problem.test_cases.all())
        total_tests = len(test_cases)

        # Update initial state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': total_tests,
                'status': 'Starting execution...'
            }
        )

        # Execute code with progress tracking
        test_results = []
        passed_count = 0
        failed_count = 0
        results = []
        history_results = []

        for idx, tc in enumerate(test_cases, 1):
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': idx,
                    'total': total_tests,
                    'status': f'Testing {idx}/{total_tests}...'
                }
            )

            # Execute single test case
            test_input = tc.input
            single_result = CodeExecutionService.execute_with_test_cases(
                code=code,
                language=language,
                test_inputs=[test_input]
            )[0]

            result = single_result
            passed = result['status'] == 'success' and result['output'].strip() == tc.output.strip()

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            # For frontend - includes input and expected
            results.append({
                'test_case_id': tc.id,
                'input': tc.input,
                'expected': tc.output,
                'output': result.get('output', ''),
                'passed': passed,
                'error': result.get('error'),
                'status': result['status']
            })

            # For database - only output (smaller storage)
            history_results.append({
                'test_case_id': tc.id,
                'output': result.get('output', ''),
                'passed': passed,
                'error': result.get('error'),
                'status': result['status']
            })

        # Save to search history
        execution_id = None
        try:
            # OPTIMIZATION: Fetch user with only() if needed
            user = None
            if user_id:
                user = User.objects.only('id').filter(id=user_id).first()

            # OPTIMIZATION: Create history record in single query
            history = SearchHistory.objects.create(
                user=user,
                user_identifier=user_identifier,
                problem=problem,
                platform=problem.platform,
                problem_number=problem.problem_id,
                problem_title=problem.title,
                language=language,
                code=code,
                result_summary='Passed' if failed_count == 0 else 'Failed',
                passed_count=passed_count,
                failed_count=failed_count,
                total_count=len(test_cases),
                is_code_public=is_code_public,
                test_results=history_results
            )
            execution_id = history.id

            # OPTIMIZATION: Update problem execution count in metadata
            # Using update_fields for targeted update
            if not problem.metadata:
                problem.metadata = {}
            problem.metadata['execution_count'] = problem.metadata.get('execution_count', 0) + 1
            problem.save(update_fields=['metadata'])

            logger.info(
                f"Code execution saved: problem={problem_id}, user={user_identifier}, "
                f"passed={passed_count}/{len(test_cases)}"
            )

        except Exception as e:
            logger.error(f"Failed to save search history: {str(e)}", exc_info=True)

        return {
            'status': 'COMPLETED',
            'execution_id': execution_id,
            'results': results,
            'summary': {
                'total': len(test_cases),
                'passed': passed_count,
                'failed': failed_count
            }
        }

    except Problem.DoesNotExist:
        logger.error(f"Problem {problem_id} not found")
        return {
            'status': 'FAILED',
            'error': 'Problem not found'
        }

    except Exception as e:
        logger.error(f"Error in execute_code_task for problem {problem_id}: {str(e)}", exc_info=True)
        # Don't retry - handled by autoretry_for
        raise


# ============================================================================
# OPTIMIZED PROBLEM INFO EXTRACTION TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540,  # 9 minutes soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def extract_problem_info_task(self, problem_url, job_id=None, additional_context=None):
    """
    Async task to extract problem information from URL using Gemini AI

    OPTIMIZATIONS:
    - Use only() + update_fields for minimal database updates
    - Cache problem info for repeated requests (only if no additional context)
    - Early validation and exit
    - Proper exception handling with logging

    Args:
        problem_url: URL of the problem page
        job_id: Optional ScriptGenerationJob ID to update
        additional_context: Optional additional context (e.g., counterexamples, edge cases)
                           to help AI generate better solution

    Returns:
        dict: {
            'status': 'COMPLETED',
            'title': str,
            'constraints': str,
            'solution_code': str,
            'platform': str,
            'problem_id': str
        }
    """
    logger.info(f"[Worker] extract_problem_info_task received - URL: {problem_url}, Job ID: {job_id}, Additional Context: {bool(additional_context)}")

    try:
        # OPTIMIZATION: Check cache first (skip if additional context provided)
        cache_key = f"problem_info:{problem_url}"
        cached_info = None
        if not additional_context:
            cached_info = cache.get(cache_key)

        # Update job status if job_id provided
        if job_id:
            try:
                job = ProblemExtractionJob.objects.only(
                    'id', 'status', 'celery_task_id', 'platform', 'problem_id'
                ).get(id=job_id)
                job.status = 'PROCESSING'
                job.celery_task_id = self.request.id
                job.save(update_fields=['status', 'celery_task_id'])
                logger.info(f"[Worker] Job {job_id} status updated to PROCESSING")

                # Update Problem metadata to PROCESSING
                try:
                    from api.models import Problem
                    problem = Problem.objects.get(
                        platform=job.platform,
                        problem_id=job.problem_id
                    )
                    problem.metadata = {
                        **(problem.metadata or {}),
                        'extraction_status': 'PROCESSING',
                        'extraction_job_id': job_id
                    }
                    problem.save(update_fields=['metadata'])
                    logger.info(f"[Worker] Problem {job.platform}/{job.problem_id} status updated to PROCESSING")
                except Exception as e:
                    logger.warning(f"[Worker] Problem not found for {job.platform}/{job.problem_id}: {e}")
            except ProblemExtractionJob.DoesNotExist:
                logger.warning(f"[Worker] Job {job_id} not found for problem extraction")

        # Extract platform and problem_id from URL
        logger.info(f"[Worker] Parsing URL: {problem_url}")
        platform, problem_id = _parse_problem_url(problem_url)
        logger.info(f"[Worker] Parsed - Platform: {platform}, Problem ID: {problem_id}")

        # Helper function to update progress
        def update_progress(progress_message, status='in_progress'):
            """Update Problem with progress message and save to JobProgressHistory"""
            logger.info(f"[Progress] {progress_message}")

            if not job_id:
                return

            try:
                # Update Problem metadata
                from api.models import Problem
                problem = Problem.objects.get(
                    platform=platform,
                    problem_id=problem_id
                )
                problem.metadata = {
                    **(problem.metadata or {}),
                    'extraction_status': 'PROCESSING',
                    'extraction_job_id': job_id,
                    'progress': progress_message
                }
                problem.save(update_fields=['metadata'])

                # Save to JobProgressHistory
                job = ProblemExtractionJob.objects.get(id=job_id)
                content_type = ContentType.objects.get_for_model(ProblemExtractionJob)
                JobProgressHistory.objects.create(
                    content_type=content_type,
                    object_id=job.id,
                    step=progress_message[:100],  # Limit step name to 100 chars
                    message=progress_message,
                    status=status
                )
            except Exception as e:
                logger.error(f"[Progress] Failed to update progress: {e}")

        # Use cached info if available
        if cached_info:
            logger.info(f"Using cached problem info for {problem_url}")
            update_progress("Loading from cache...")
            problem_info = cached_info
        else:
            # Use Gemini to extract problem info
            update_progress("Fetching webpage...")
            gemini_service = GeminiService()
            problem_info = gemini_service.extract_problem_info_from_url(
                problem_url,
                progress_callback=update_progress,
                additional_context=additional_context
            )

            # OPTIMIZATION: Cache the result
            cache.set(cache_key, problem_info, CACHE_TTL_LONG)

        # Update job with results if job_id provided
        if job_id:
            try:
                job = ProblemExtractionJob.objects.only(
                    'id', 'status'
                ).get(id=job_id)
                job.status = 'COMPLETED'
                job.save(update_fields=['status'])

                # Create or update Problem as draft
                from api.models import Problem
                problem, created = Problem.objects.get_or_create(
                    platform=platform,
                    problem_id=problem_id,
                    defaults={
                        'title': problem_info['title'],
                        'problem_url': problem_url,
                        'constraints': problem_info['constraints'],
                        'solution_code': problem_info['solution_code'],
                        'language': 'cpp',
                        'tags': [],
                        'is_completed': False,  # Draft state
                        'metadata': {
                            'extraction_job_id': job_id,
                            'extraction_status': 'COMPLETED'
                        }
                    }
                )

                if not created:
                    # Update existing problem INCLUDING TITLE
                    problem.title = problem_info['title']  # Update to real extracted title
                    problem.problem_url = problem_url
                    problem.constraints = problem_info['constraints']
                    problem.solution_code = problem_info['solution_code']
                    problem.language = 'cpp'
                    problem.metadata = {
                        **problem.metadata,
                        'extraction_job_id': job_id,
                        'extraction_status': 'COMPLETED',
                        'extracted_title': problem_info['title']  # Store extracted title in metadata
                    }
                    problem.save(update_fields=[
                        'title', 'problem_url', 'constraints', 'solution_code',
                        'language', 'metadata'
                    ])
                    logger.info(f"Updated problem {problem.id} with extracted title: {problem_info['title']}")

                logger.info(f"Problem {platform}/{problem_id} {'created' if created else 'updated'} from job {job_id}")

            except ProblemExtractionJob.DoesNotExist:
                logger.warning(f"Job {job_id} not found for final update")

        return {
            'status': 'COMPLETED',
            'title': problem_info['title'],
            'constraints': problem_info['constraints'],
            'solution_code': problem_info['solution_code'],
            'platform': platform,
            'problem_id': problem_id,
            'language': 'cpp'
        }

    except Exception as e:
        logger.error(f"Error in extract_problem_info_task for {problem_url}: {str(e)}", exc_info=True)

        # Update job with error if job_id provided
        if job_id:
            try:
                job = ProblemExtractionJob.objects.only(
                    'id', 'status', 'error_message', 'platform', 'problem_id'
                ).get(id=job_id)
                job.status = 'FAILED'
                job.error_message = str(e)
                job.save(update_fields=['status', 'error_message'])

                # Update Problem metadata to FAILED
                try:
                    from api.models import Problem
                    problem = Problem.objects.get(
                        platform=job.platform,
                        problem_id=job.problem_id
                    )
                    problem.metadata = {
                        **(problem.metadata or {}),
                        'extraction_status': 'FAILED',
                        'extraction_job_id': job_id,
                        'extraction_error': str(e)
                    }
                    problem.save(update_fields=['metadata'])
                    logger.info(f"[Worker] Problem {job.platform}/{job.problem_id} status updated to FAILED")
                except Exception as ex:
                    logger.warning(f"[Worker] Problem not found for {job.platform}/{job.problem_id}: {ex}")
            except ProblemExtractionJob.DoesNotExist:
                logger.warning(f"Job {job_id} not found for error update")

        # Don't retry - handled by autoretry_for
        raise


def _parse_problem_url(url):
    """
    Parse problem URL to extract platform and problem_id

    Args:
        url: Problem URL

    Returns:
        tuple: (platform, problem_id)

    Raises:
        ValueError: If URL format is not recognized
    """
    # Baekjoon
    if 'acmicpc.net' in url or 'baekjoon' in url.lower():
        match = re.search(r'/problem/(\d+)', url)
        if match:
            return ('baekjoon', match.group(1))

    # Codeforces
    if 'codeforces.com' in url:
        match = re.search(r'/problemset/problem/(\d+)/([A-Z]\d?)', url, re.IGNORECASE)
        if match:
            return ('codeforces', f"{match.group(1)}{match.group(2).upper()}")
        match = re.search(r'/contest/(\d+)/problem/([A-Z]\d?)', url, re.IGNORECASE)
        if match:
            return ('codeforces', f"{match.group(1)}{match.group(2).upper()}")

    # LeetCode
    if 'leetcode.com' in url:
        match = re.search(r'/problems/([^/]+)', url)
        if match:
            return ('leetcode', match.group(1))

    # AtCoder
    if 'atcoder.jp' in url:
        match = re.search(r'/tasks/([^/]+)', url)
        if match:
            return ('atcoder', match.group(1))

    # Default: try to extract from URL path
    parts = url.rstrip('/').split('/')
    if len(parts) >= 2:
        return ('unknown', parts[-1])

    raise ValueError(f'Unable to parse problem URL: {url}')


# ============================================================================
# OPTIMIZED HINTS GENERATION TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540,  # 9 minutes soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_hints_task(self, history_id):
    """
    Async task to generate hints for a failed code execution

    OPTIMIZATIONS:
    - Use select_related to avoid N+1 query on problem
    - Use only() to fetch minimal fields
    - Early validation and exit conditions
    - Cache hints to avoid regeneration
    - Efficient data extraction

    Args:
        history_id: ID of the SearchHistory record

    Returns:
        dict: Result with status and hints
    """
    logger.info(f"[HINTS] Starting hint generation for history {history_id}")

    try:
        # OPTIMIZATION: Use select_related + only() to minimize queries
        logger.info(f"[HINTS] Fetching history record {history_id} from database")
        history = SearchHistory.objects.select_related('problem').only(
            'id', 'code', 'language', 'test_results', 'failed_count', 'hints',
            'problem__id', 'problem__solution_code', 'problem__title',
            'problem__platform', 'problem__problem_id', 'problem__language'
        ).get(id=history_id)
        logger.info(f"[HINTS] Retrieved history {history_id}: problem={history.problem.title}, failed_count={history.failed_count}, language={history.language}")

        # Early validation: Check if there are any failures
        if history.failed_count == 0:
            logger.info(f"History {history_id} has no failures, hints not needed")
            return {
                'status': 'FAILED',
                'error': 'No failed test cases - hints not needed'
            }

        # Early exit: Check if hints already exist
        if history.hints:
            logger.info(f"History {history_id} already has hints")
            return {
                'status': 'COMPLETED',
                'hints': history.hints,
                'message': 'Hints already exist'
            }

        # Validate problem has solution code
        if not history.problem.solution_code:
            logger.warning(f"History {history_id} - problem has no solution code")
            return {
                'status': 'FAILED',
                'error': 'No solution code available for this problem'
            }

        # OPTIMIZATION: Extract failed tests efficiently
        failed_tests = [
            result for result in (history.test_results or [])
            if not result.get('passed', False)
        ]

        if not failed_tests:
            logger.warning(f"[HINTS] History {history_id} has no failed test case details")
            return {
                'status': 'FAILED',
                'error': 'No failed test case details available'
            }

        logger.info(f"[HINTS] History {history_id}: Found {len(failed_tests)} failed tests")

        # Decode solution code (it's stored as base64)
        try:
            solution_code = base64.b64decode(history.problem.solution_code).decode('utf-8')
            logger.info(f"[HINTS] History {history_id}: Successfully decoded solution code")
        except Exception as e:
            # If decoding fails, use as-is (for backwards compatibility)
            logger.warning(f"[HINTS] History {history_id}: Failed to decode solution code, using as-is: {e}")
            solution_code = history.problem.solution_code

        # Prepare problem info
        problem_info = {
            'title': history.problem.title,
            'platform': history.problem.platform,
            'problem_id': history.problem.problem_id,
            'language': history.language
        }

        # Generate hints using Gemini
        logger.info(f"[HINTS] History {history_id}: Calling Gemini API to generate hints")
        gemini_service = GeminiService()
        hints = gemini_service.generate_hints(
            user_code=history.code,
            solution_code=solution_code,
            test_failures=failed_tests,
            problem_info=problem_info
        )
        logger.info(f"[HINTS] History {history_id}: Gemini API returned {len(hints) if hints else 0} hints")

        # OPTIMIZATION: Save hints to history record (use update_fields)
        logger.info(f"[HINTS] History {history_id}: Saving hints to database")
        history.hints = hints
        history.save(update_fields=['hints'])
        logger.info(f"[HINTS] History {history_id}: Successfully saved {len(hints)} hints to database")

        logger.info(f"[HINTS] History {history_id}: Task completed successfully with {len(hints)} hints")

        return {
            'status': 'COMPLETED',
            'hints': hints,
            'message': f'Generated {len(hints)} hints successfully'
        }

    except SearchHistory.DoesNotExist:
        logger.error(f"[HINTS] History {history_id}: SearchHistory not found in database")
        return {
            'status': 'FAILED',
            'error': 'Search history not found'
        }

    except Exception as e:
        logger.error(f"[HINTS] History {history_id}: Task failed with error: {str(e)}", exc_info=True)
        # Don't retry - handled by autoretry_for
        raise


# ============================================================================
# OPTIMIZED DELETE JOB TASK
# ============================================================================
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=60,  # 1 minute hard limit
    soft_time_limit=50,  # 50 seconds soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    ignore_result=True,  # No need to store result for delete operations
)
def delete_job_task(self, job_id):
    """
    Async task to delete a ScriptGenerationJob record

    OPTIMIZATIONS:
    - Use only() to fetch minimal fields
    - Ignore result to save space
    - Fast execution with minimal overhead

    Args:
        job_id: ID of the ScriptGenerationJob to delete

    Returns:
        dict: Result with job_id and status
    """
    try:
        # OPTIMIZATION: Use only() to fetch minimal fields before deletion
        job = ScriptGenerationJob.objects.only('id').get(id=job_id)

        # Delete the job
        job.delete()

        logger.info(f"Deleted job {job_id}")

        return {
            'status': 'COMPLETED',
            'job_id': job_id,
            'message': f'Job {job_id} deleted successfully'
        }

    except ScriptGenerationJob.DoesNotExist:
        logger.error(f"Job {job_id} not found for deletion")
        return {
            'status': 'FAILED',
            'error': 'Job not found'
        }

    except Exception as e:
        logger.error(f"Error in delete_job_task for job {job_id}: {str(e)}", exc_info=True)
        # Don't retry - handled by autoretry_for
        raise


# ============================================================================
# CACHE WARMING TASKS
# ============================================================================
@shared_task(
    bind=True,
    max_retries=2,
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
    ignore_result=True,
)
def warm_problem_cache_task(self):
    """
    Warm cache for frequently accessed problem data

    This task pre-populates the cache with:
    - All completed problems list
    - Popular problem details
    - Problem counts by platform

    Scheduled to run periodically (e.g., every 5 minutes)
    """
    from .serializers import ProblemListSerializer, ProblemSerializer
    from .utils.cache import CacheKeyGenerator
    from django.conf import settings

    try:
        logger.info("Starting cache warming task for problems...")

        # 1. Warm cache for completed problems list (main endpoint)
        cache_key = CacheKeyGenerator.problem_list_key()
        queryset = Problem.objects.minimal_fields().with_test_case_count().completed().order_by('-created_at')
        serializer = ProblemListSerializer(queryset, many=True)
        ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)
        cache.set(cache_key, serializer.data, ttl)
        logger.info(f"Warmed cache: {cache_key} ({len(serializer.data)} problems)")

        # 2. Warm cache for registered problems endpoint
        cache_key = "problem_registered:all"
        cache.set(cache_key, {'problems': serializer.data}, ttl)
        logger.info(f"Warmed cache: {cache_key}")

        # 3. Warm cache for platform-specific problem lists
        platforms = Problem.objects.values_list('platform', flat=True).distinct()
        for platform in platforms:
            cache_key = CacheKeyGenerator.problem_list_key(platform=platform)
            queryset = Problem.objects.minimal_fields().with_test_case_count().completed().filter(
                platform=platform
            ).order_by('-created_at')
            serializer = ProblemListSerializer(queryset, many=True)
            cache.set(cache_key, serializer.data, ttl)
            logger.info(f"Warmed cache: {cache_key} ({len(serializer.data)} problems)")

        # 4. Warm cache for most recently accessed problem details (top 20)
        recent_problems = Problem.objects.with_test_cases().completed().order_by('-created_at')[:20]
        ttl_detail = settings.CACHE_TTL.get('PROBLEM_DETAIL', 600)
        for problem in recent_problems:
            cache_key = CacheKeyGenerator.problem_detail_key(problem_id=problem.id)
            serializer = ProblemSerializer(problem)
            cache.set(cache_key, serializer.data, ttl_detail)

        logger.info(f"Warmed cache for {len(recent_problems)} problem details")

        # 5. Warm cache for draft problems
        cache_key = "problem_drafts:all"
        queryset = Problem.objects.minimal_fields().with_test_case_count().drafts().order_by('-created_at')
        serializer = ProblemListSerializer(queryset, many=True)
        ttl_short = settings.CACHE_TTL.get('SHORT', 60)
        cache.set(cache_key, {'drafts': serializer.data}, ttl_short)
        logger.info(f"Warmed cache: {cache_key} ({len(serializer.data)} drafts)")

        logger.info("Cache warming task completed successfully")
        return {'status': 'SUCCESS', 'message': 'Problem cache warmed successfully'}

    except Exception as e:
        logger.error(f"Error in warm_problem_cache_task: {str(e)}", exc_info=True)
        raise


@shared_task(
    bind=True,
    max_retries=2,
    time_limit=300,  # 5 minutes
    soft_time_limit=270,
    ignore_result=True,
)
def warm_user_stats_cache_task(self, user_ids=None):
    """
    Warm cache for user statistics

    Args:
        user_ids: List of user IDs to warm cache for (default: active users)

    This task pre-populates the cache with user statistics for active users
    """
    from .utils.cache import CacheKeyGenerator
    from django.conf import settings
    from django.db.models import Count, Q

    try:
        logger.info("Starting cache warming task for user stats...")

        # If no user_ids provided, get recently active users
        if not user_ids:
            # Get users who have search history in the last 7 days
            from datetime import timedelta
            from django.utils import timezone
            week_ago = timezone.now() - timedelta(days=7)

            user_ids = SearchHistory.objects.filter(
                created_at__gte=week_ago,
                user__isnull=False
            ).values_list('user_id', flat=True).distinct()

        warmed_count = 0
        for user_id in user_ids:
            try:
                cache_key = CacheKeyGenerator.user_stats_key(user_id)

                # Calculate stats
                user_history = SearchHistory.objects.filter(user_id=user_id).only(
                    'id', 'platform', 'language', 'problem_id', 'failed_count'
                )

                total_executions = user_history.count()
                platform_stats = user_history.values('platform').annotate(count=Count('id')).order_by()
                by_platform = {stat['platform']: stat['count'] for stat in platform_stats}

                language_stats = user_history.values('language').annotate(count=Count('id')).order_by()
                by_language = {stat['language']: stat['count'] for stat in language_stats}

                total_problems = user_history.values('problem').distinct().count()

                pass_fail_stats = user_history.aggregate(
                    passed=Count('id', filter=Q(failed_count=0)),
                    failed=Count('id', filter=Q(failed_count__gt=0))
                )

                response_data = {
                    'total_executions': total_executions,
                    'by_platform': by_platform,
                    'by_language': by_language,
                    'total_problems': total_problems,
                    'passed_executions': pass_fail_stats['passed'],
                    'failed_executions': pass_fail_stats['failed']
                }

                # Cache the result
                ttl = settings.CACHE_TTL.get('USER_STATS', 180)
                cache.set(cache_key, response_data, ttl)
                warmed_count += 1

            except Exception as e:
                logger.error(f"Error warming cache for user {user_id}: {str(e)}")
                continue

        logger.info(f"Cache warming task completed. Warmed {warmed_count} user stats")
        return {'status': 'SUCCESS', 'warmed_count': warmed_count}

    except Exception as e:
        logger.error(f"Error in warm_user_stats_cache_task: {str(e)}", exc_info=True)
        raise


@shared_task(
    bind=True,
    max_retries=1,
    time_limit=60,
    soft_time_limit=50,
    ignore_result=True,
)
def invalidate_cache_task(self, cache_pattern):
    """
    Invalidate cache entries matching a pattern

    Args:
        cache_pattern: Pattern to match cache keys (e.g., 'problem_*', 'user_stats:*')

    Usage:
        invalidate_cache_task.delay('problem_*')
    """
    from .utils.cache import CacheInvalidator

    try:
        count = CacheInvalidator.invalidate_pattern(cache_pattern)
        logger.info(f"Invalidated {count} cache entries matching pattern: {cache_pattern}")
        return {'status': 'SUCCESS', 'invalidated_count': count}

    except Exception as e:
        logger.error(f"Error in invalidate_cache_task: {str(e)}", exc_info=True)
        raise


# ============================================================================
# ORPHANED JOB RECOVERY TASK (Maintenance)
# ============================================================================
@shared_task(
    bind=True,
    name='api.tasks.recover_orphaned_jobs_task',
    max_retries=1,
    time_limit=300,  # 5 minutes hard limit
    soft_time_limit=240,  # 4 minutes soft limit
)
def recover_orphaned_jobs_task(self, timeout_minutes=30):
    """
    Periodic task to recover orphaned jobs stuck in PROCESSING state

    This task should be scheduled to run periodically (e.g., every 15 minutes)
    using Celery Beat to automatically detect and recover jobs that have
    been stuck in PROCESSING state due to worker crashes or restarts.

    Args:
        timeout_minutes: Jobs in PROCESSING state for longer than this will be marked as FAILED

    Returns:
        Dict with recovery statistics
    """
    from django.utils import timezone
    from datetime import timedelta

    logger.info(f"[Orphaned Job Recovery] Starting recovery task (timeout: {timeout_minutes} min)")

    try:
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)

        # Find orphaned extraction jobs
        orphaned_extraction = ProblemExtractionJob.objects.filter(
            status='PROCESSING',
            updated_at__lt=cutoff_time
        )

        # Find orphaned generation jobs
        orphaned_generation = ScriptGenerationJob.objects.filter(
            status='PROCESSING',
            updated_at__lt=cutoff_time
        )

        extraction_count = orphaned_extraction.count()
        generation_count = orphaned_generation.count()
        total_count = extraction_count + generation_count

        if total_count == 0:
            logger.info("[Orphaned Job Recovery] No orphaned jobs found")
            return {
                'status': 'SUCCESS',
                'found_count': 0,
                'recovered_count': 0
            }

        logger.warning(f"[Orphaned Job Recovery] Found {total_count} orphaned job(s): "
                      f"{extraction_count} extraction, {generation_count} generation")

        # Process extraction jobs: delete if Problem doesn't exist, otherwise mark as FAILED
        deleted_count = 0
        failed_count = 0
        updated_problems = 0

        for job in orphaned_extraction:
            try:
                problem = Problem.objects.get(
                    platform=job.platform,
                    problem_id=job.problem_id
                )
                # Problem exists - mark job as FAILED
                job.status = 'FAILED'
                job.error_message = f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
                job.save(update_fields=['status', 'error_message'])
                failed_count += 1

                # Update Problem metadata
                problem.metadata = {
                    **(problem.metadata or {}),
                    'extraction_status': 'FAILED',
                    'extraction_job_id': job.id,
                    'error_message': 'Job orphaned and automatically recovered'
                }
                problem.save(update_fields=['metadata'])
                updated_problems += 1
                logger.info(f"[Orphaned Job Recovery] Marked job #{job.id} as FAILED and updated Problem {job.platform}/{job.problem_id}")

            except Problem.DoesNotExist:
                # Problem doesn't exist - delete the job
                job_id = job.id
                platform = job.platform
                problem_id = job.problem_id
                job.delete()
                deleted_count += 1
                logger.info(f"[Orphaned Job Recovery] Deleted orphaned job #{job_id} (Problem {platform}/{problem_id} not found)")

        # Mark generation jobs as failed
        updated_generation = orphaned_generation.update(
            status='FAILED',
            error_message=f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
        )

        total_recovered = failed_count + updated_generation

        logger.info(f"[Orphaned Job Recovery] Successfully processed {total_count} job(s): "
                   f"{deleted_count} deleted, {failed_count} marked FAILED, {updated_generation} generation jobs FAILED, "
                   f"{updated_problems} problems updated")

        return {
            'status': 'SUCCESS',
            'found_count': total_count,
            'recovered_count': total_recovered,
            'deleted_count': deleted_count,
            'extraction_jobs_failed': failed_count,
            'generation_jobs_failed': updated_generation,
            'problems_updated': updated_problems
        }

    except Exception as e:
        logger.error(f"[Orphaned Job Recovery] Error: {str(e)}", exc_info=True)
        raise
