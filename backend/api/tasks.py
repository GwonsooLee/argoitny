"""Celery tasks for async processing - Migrated to DynamoDB"""
from celery import shared_task
from django.core.cache import cache
from .services.llm_factory import LLMServiceFactory
from .services.code_execution_service import CodeExecutionService
from .utils.job_helper import JobHelper
from .tasks_solution_generation import generate_solution_with_fallback
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
    acks_late=False,  # ACK immediately on consume to prevent duplicate execution
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
        # ATOMIC IDEMPOTENCY CHECK: Try to atomically update status from PENDING to PROCESSING
        # This prevents race conditions when multiple workers consume the same message
        logger.info(f"[generate_script_task] Attempting to claim job {job_id}")
        success, job = JobHelper.conditional_update_script_job_to_processing(
            job_id=job_id,
            celery_task_id=self.request.id,
            expected_status='PENDING'
        )

        if not success:
            # Another worker already claimed this job - this is normal behavior
            logger.info(f"[generate_script_task] Job {job_id} already claimed by another worker, skipping (race condition prevented)")
            return {
                'job_id': job_id,
                'status': 'SKIPPED',
                'message': 'Job already claimed by another worker'
            }

        logger.info(f"[generate_script_task] Job {job_id} successfully claimed: {job['platform']}/{job['problem_id']} - {job['title']}")

        # Fetch solution_code from existing Problem using DynamoDB
        from api.dynamodb.repositories import ProblemRepository

        solution_code = ''
        problem_repo = ProblemRepository()
        problem = problem_repo.get_problem(
            platform=job['platform'],
            problem_id=job['problem_id']
        )

        if not problem:
            logger.warning(f"[generate_script_task] Problem not found: {job['platform']}/{job['problem_id']}")
            raise ValueError(f"Problem {job['platform']}/{job['problem_id']} not found. Script generation requires existing problem with solution code.")

        solution_code = problem.get('solution_code', '')
        logger.info(f"[generate_script_task] Fetched solution_code from Problem ({len(solution_code)} chars)")

        # Prepare problem info for Gemini
        problem_info = {
            'platform': job['platform'],
            'problem_id': job['problem_id'],
            'title': job['title'],
            'solution_code': solution_code,
            'language': job['language'],
            'constraints': job['constraints'],
            'tags': job.get('tags', []),
        }
        logger.info(f"[generate_script_task] Prepared problem info for job {job_id}")
        logger.info(f"[generate_script_task] Constraints: {job['constraints'][:200]}...")

        # Check if there's a previous failure to learn from
        previous_failure = None
        if job.get('generator_code') and job.get('error_message'):
            # This is a retry - provide context about previous failure
            previous_failure = {
                'code': job['generator_code'],
                'error': job['error_message']
            }
            logger.info(f"[generate_script_task] Retry attempt with previous failure context")
            logger.info(f"[generate_script_task] Previous error: {job['error_message'][:200]}...")

        # Generate script using LLM service (Gemini or OpenAI based on settings)
        logger.info(f"[generate_script_task] Calling LLM API to generate test case generator...")
        llm_service = LLMServiceFactory.create_service()
        generator_code = llm_service.generate_test_case_generator_code(problem_info, previous_failure=previous_failure)
        logger.info(f"[generate_script_task] Gemini returned generator code ({len(generator_code)} chars)")

        # VALIDATION: Check for placeholder code
        if '"""' in generator_code or '"..."' in generator_code or "case_data = '...'" in generator_code:
            logger.error(f"[generate_script_task] Generated code contains placeholder strings!")
            raise ValueError("Generated code contains placeholder strings - Gemini did not generate actual test case logic")

        # Update job with result
        logger.info(f"[generate_script_task] Updating job {job_id} status to COMPLETED")
        job = JobHelper.update_script_generation_job(job_id, {
            'status': 'COMPLETED',
            'generator_code': generator_code
        })

        # Execute generator code to create test cases and save to Problem
        try:
            from .services.test_case_generator import TestCaseGenerator

            # Generate test cases using the script
            test_case_inputs = TestCaseGenerator.execute_generator_code(
                code=generator_code,
                num_cases=10
            )

            # Update problem metadata using DynamoDB (problem and solution_code already exist)
            problem_updates = {
                'title': job['title'],
                'problem_url': job.get('problem_url') or '',
                'tags': job.get('tags', []),
                'language': job['language'],
                'constraints': job['constraints']
            }

            problem_repo.update_problem(
                platform=job['platform'],
                problem_id=job['problem_id'],
                updates=problem_updates
            )

            # Reload problem instance
            problem = problem_repo.get_problem(
                platform=job['platform'],
                problem_id=job['problem_id']
            )

            # Execute solution code with generated inputs to get outputs
            test_results = CodeExecutionService.execute_with_test_cases(
                code=solution_code,
                language=job['language'],
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

            # Prepare test cases for S3 storage
            testcases_for_s3 = []
            for idx, r in enumerate(r for r in test_results if r['status'] == 'success'):
                testcases_for_s3.append({
                    'testcase_id': str(idx + 1),
                    'input': r['input'],
                    'output': r['output']
                })

            # Store all test cases in S3 as a single file
            if testcases_for_s3:
                from api.services.s3_testcase_service import S3TestCaseService
                s3_service = S3TestCaseService()

                try:
                    s3_service.store_testcases(
                        platform=job['platform'],
                        problem_id=job['problem_id'],
                        testcases=testcases_for_s3
                    )

                    # Update problem metadata to reflect S3 storage
                    problem_repo.update_problem(
                        platform=job['platform'],
                        problem_id=job['problem_id'],
                        updates={
                            'test_case_count': len(testcases_for_s3)
                        }
                    )

                    logger.info(f"Stored {len(testcases_for_s3)} test cases in S3")
                except Exception as e:
                    logger.error(f"Failed to store test cases in S3: {e}")
                    raise
                logger.info(f"Problem remains in draft state - admin review required")
            else:
                logger.warning(f"No successful test cases generated")

        except Exception as e:
            # Log but don't fail the task if test case generation fails
            logger.error(f"Failed to generate/save test cases for job {job_id}: {str(e)}", exc_info=True)

        return {
            'job_id': job_id,
            'status': 'COMPLETED',
            'message': 'Script generated successfully'
        }

    except Exception as e:
        logger.error(f"Error in generate_script_task for job {job_id}: {str(e)}", exc_info=True)

        # Update job with error
        try:
            JobHelper.update_script_generation_job(job_id, {
                'status': 'FAILED',
                'error_message': str(e)
            })
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
    acks_late=False,  # ACK immediately on consume to prevent duplicate execution
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_outputs_task(self, platform, problem_id):
    """
    Async task to generate outputs for test cases using solution code

    Args:
        platform: Platform name (e.g., 'baekjoon', 'codeforces')
        problem_id: Problem ID

    Returns:
        dict: Result with status and count
    """
    try:
        from api.dynamodb.repositories import ProblemRepository

        problem_repo = ProblemRepository()

        # Get problem with test cases from DynamoDB
        problem_with_tests = problem_repo.get_problem_with_testcases(
            platform=platform,
            problem_id=problem_id
        )

        if not problem_with_tests:
            logger.error(f"Problem {platform}/{problem_id} not found")
            return {
                'status': 'FAILED',
                'error': 'Problem not found'
            }

        # Early validation
        solution_code = problem_with_tests.get('solution_code', '')
        if not solution_code:
            logger.warning(f"Problem {platform}/{problem_id} has no solution code")
            return {
                'status': 'FAILED',
                'error': 'Problem has no solution code'
            }

        test_cases = problem_with_tests.get('test_cases', [])
        if not test_cases:
            logger.warning(f"Problem {platform}/{problem_id} has no test cases")
            return {
                'status': 'FAILED',
                'error': 'Problem has no test cases'
            }

        # Extract inputs
        test_inputs = [tc['input'] for tc in test_cases]

        # Execute solution code with test inputs (solution_code already decoded by repository)
        test_results = CodeExecutionService.execute_with_test_cases(
            code=solution_code,
            language=problem_with_tests.get('language') or 'python',
            test_inputs=test_inputs
        )

        # Update test case outputs in DynamoDB
        failed_cases = []
        success_count = 0

        for tc, result in zip(test_cases, test_results):
            if result['status'] == 'success':
                # Update test case output
                pk = f"PROB#{platform}#{problem_id}"
                sk = f"TC#{tc['testcase_id']}"
                problem_repo.update_item(
                    pk=pk,
                    sk=sk,
                    update_expression='SET dat.#out = :out',
                    expression_attribute_values={':out': result['output']},
                    expression_attribute_names={'#out': 'out'}
                )
                success_count += 1
            else:
                failed_cases.append({
                    'input': result.get('input', '')[:50],
                    'error': result.get('error', 'Unknown error')
                })

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
    acks_late=False,  # ACK immediately on consume to prevent duplicate execution
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def execute_code_task(self, code, language, platform=None, problem_identifier=None, problem_id=None, user_id=None, user_identifier='anonymous', is_code_public=False):
    """
    Async task to execute code against test cases - DynamoDB implementation

    OPTIMIZATIONS:
    - DynamoDB repository for test case retrieval (single query)
    - Fallback to Django ORM for backward compatibility
    - Use only() to fetch minimal problem fields
    - Efficient list comprehensions for result building
    - Single transaction for history creation

    Args:
        code: User's code
        language: Programming language
        platform: Platform name (e.g., 'baekjoon', 'codeforces') - New approach
        problem_identifier: Problem identifier on platform - New approach
        problem_id: Problem ID (legacy, for backward compatibility)
        user_id: User ID (if authenticated)
        user_identifier: User email or identifier
        is_code_public: Whether to make code public

    Returns:
        dict: Execution results
    """
    from api.dynamodb.client import DynamoDBClient
    from api.dynamodb.repositories import ProblemRepository
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Determine platform and problem_identifier
        if platform and problem_identifier:
            # New approach: Use DynamoDB directly
            table = DynamoDBClient.get_table()
            problem_repo = ProblemRepository(table)

            # Get problem with test cases from DynamoDB
            problem_data = problem_repo.get_problem_with_testcases(
                platform=platform,
                problem_id=problem_identifier
            )

            if not problem_data:
                logger.error(f"Problem {platform}/{problem_identifier} not found in DynamoDB")
                return {
                    'status': 'FAILED',
                    'error': f'Problem not found: {platform}/{problem_identifier}'
                }

            # Extract test cases
            test_cases_data = problem_data.get('test_cases', [])
            if not test_cases_data:
                logger.warning(f"Problem {platform}/{problem_identifier} has no test cases in DynamoDB")
                return {
                    'status': 'FAILED',
                    'error': 'No test cases available for this problem'
                }

            # Convert DynamoDB test cases to expected format
            test_cases = []
            for tc in test_cases_data:
                test_cases.append({
                    'id': tc['testcase_id'],
                    'input': tc['input'],
                    'output': tc['output']
                })

        else:
            logger.error("Platform and problem_identifier are required")
            return {
                'status': 'FAILED',
                'error': 'Platform and problem_identifier are required'
            }

        # Now we have test_cases in the expected format
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
            test_input = tc['input']
            single_result = CodeExecutionService.execute_with_test_cases(
                code=code,
                language=language,
                test_inputs=[test_input]
            )[0]

            result = single_result
            passed = result['status'] == 'success' and result['output'].strip() == tc['output'].strip()

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            # For frontend - includes input and expected
            results.append({
                'test_case_id': tc['id'],
                'input': tc['input'],
                'expected': tc['output'],
                'output': result.get('output', ''),
                'passed': passed,
                'error': result.get('error'),
                'status': result['status']
            })

            # For database - only output (smaller storage)
            history_results.append({
                'test_case_id': tc['id'],
                'output': result.get('output', ''),
                'passed': passed,
                'error': result.get('error'),
                'status': result['status']
            })

        # Save to search history in DynamoDB
        execution_id = None
        try:
            import time
            from api.dynamodb.repositories import SearchHistoryRepository

            # Get problem title for history - use DynamoDB data if ORM problem doesn't exist
            if orm_problem:
                problem_title = orm_problem.title
            elif platform and problem_identifier:
                # Fallback: get from DynamoDB data
                problem_title = problem_data.get('title', f'{platform}/{problem_identifier}')
            else:
                problem_title = f'{platform}/{problem_identifier}'

            # Generate unique history ID (timestamp-based with microsecond precision)
            history_id = int(time.time() * 1000000)

            # Convert test_results to DynamoDB format with short field names
            dynamodb_test_results = []
            for result in history_results:
                dynamodb_test_results.append({
                    'tid': result['test_case_id'],  # test_case_id
                    'out': result.get('output', ''),  # output
                    'pas': result.get('passed', False),  # passed
                    'err': result.get('error'),  # error
                    'sts': result.get('status', '')  # status
                })

            # Prepare history data with short field names for DynamoDB
            history_data = {
                'uid': user_id,  # user_id
                'uidt': user_identifier,  # user_identifier
                'pid': f'{platform}#{problem_identifier}',  # problem composite key
                'plt': platform,  # platform
                'pno': problem_identifier,  # problem_number
                'ptt': problem_title,  # problem_title
                'lng': language,  # language
                'cod': code,  # code
                'res': 'Passed' if failed_count == 0 else 'Failed',  # result_summary
                'psc': passed_count,  # passed_count
                'fsc': failed_count,  # failed_count
                'toc': len(test_cases),  # total_count
                'pub': is_code_public,  # is_code_public
                'trs': dynamodb_test_results  # test_results
            }

            # Create history in DynamoDB
            table = DynamoDBClient.get_table()
            history_repo = SearchHistoryRepository(table)
            history_repo.create_history(
                history_id=history_id,
                history_data=history_data
            )

            execution_id = history_id

            # Update problem execution count in DynamoDB metadata
            current_metadata = problem_data.get('metadata', {}) if problem_data else {}
            execution_count = current_metadata.get('execution_count', 0) + 1

            problem_repo.update_problem(
                platform=platform,
                problem_id=problem_identifier,
                updates={
                    'metadata': {
                        **current_metadata,
                        'execution_count': execution_count
                    }
                }
            )

            logger.info(
                f"Code execution saved to DynamoDB: problem={platform}/{problem_identifier}, user={user_identifier}, "
                f"passed={passed_count}/{len(test_cases)}, history_id={history_id}"
            )

        except Exception as e:
            logger.error(f"Failed to save search history to DynamoDB: {str(e)}", exc_info=True)

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

    except Exception as e:
        logger.error(f"Error in execute_code_task: {str(e)}", exc_info=True)
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
    acks_late=False,  # ACK immediately on consume to prevent duplicate execution
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

    # Initialize repositories at the beginning to avoid UnboundLocalError
    table = None
    job_repo = None
    problem_repo = None

    try:
        # OPTIMIZATION: Check cache first (skip if additional context provided)
        cache_key = f"problem_info:{problem_url}"
        cached_info = None
        if not additional_context:
            cached_info = cache.get(cache_key)

        # Update job status if job_id provided
        if job_id:
            from api.dynamodb.client import DynamoDBClient
            from api.dynamodb.repositories import ProblemExtractionJobRepository, ProblemRepository

            table = DynamoDBClient.get_table()
            job_repo = ProblemExtractionJobRepository(table)
            problem_repo = ProblemRepository(table)

            # ATOMIC IDEMPOTENCY CHECK: Try to atomically update status from PENDING to PROCESSING
            # This prevents race conditions when multiple workers consume the same message
            success, job = job_repo.conditional_update_status_to_processing(
                job_id=job_id,
                celery_task_id=self.request.id,
                expected_status='PENDING'
            )

            if not success:
                # Another worker already claimed this job - this is normal behavior with acks_late=False
                logger.info(f"[Worker] Job {job_id} already claimed by another worker, skipping (race condition prevented)")
                return {
                    'status': 'SKIPPED',
                    'message': 'Job already claimed by another worker',
                    'job_id': job_id
                }

            logger.info(f"[Worker] Job {job_id} successfully claimed and status updated to PROCESSING")

            # Update Problem metadata to PROCESSING (DynamoDB)
            try:
                # Try to get problem from DynamoDB
                problem = problem_repo.get_problem(job['platform'], job['problem_id'])
                if problem:
                    # Update metadata
                    updates = {
                        'metadata': {
                            **(problem.get('metadata') or {}),
                            'extraction_status': 'PROCESSING',
                            'extraction_job_id': job_id
                        }
                    }
                    problem_repo.update_problem(job['platform'], job['problem_id'], updates)
                    logger.info(f"[Worker] Problem {job['platform']}/{job['problem_id']} status updated to PROCESSING")
                else:
                    logger.info(f"[Worker] Problem {job['platform']}/{job['problem_id']} not created yet (will be created after extraction)")
            except Exception as e:
                logger.warning(f"[Worker] Failed to update problem metadata: {e}")

        # Extract platform and problem_id from URL
        logger.info(f"[Worker] Parsing URL: {problem_url}")
        platform, problem_id = _parse_problem_url(problem_url)
        logger.info(f"[Worker] Parsed - Platform: {platform}, Problem ID: {problem_id}")

        # Helper function to update progress
        def update_progress(progress_message, status='in_progress'):
            """
            Update Problem metadata with progress

            Args:
                progress_message: Progress message to log
                status: Progress status ('started', 'in_progress', 'completed', 'failed')
            """
            logger.info(f"[Progress] {progress_message}")

            if not job_id:
                return

            try:
                from api.dynamodb.client import DynamoDBClient
                from api.dynamodb.repositories import ProblemRepository

                table = DynamoDBClient.get_table()
                problem_repo = ProblemRepository(table)
                problem = problem_repo.get_problem(platform, problem_id)
                if problem:
                    updates = {
                        'metadata': {
                            **(problem.get('metadata') or {}),
                            'extraction_status': 'PROCESSING' if status != 'completed' else 'COMPLETED',
                            'extraction_job_id': job_id,
                            'progress': progress_message  # Keep as 'progress' for frontend compatibility
                        }
                    }
                    problem_repo.update_problem(platform, problem_id, updates)

            except Exception as e:
                logger.error(f"[Progress] Failed to update progress: {e}")

        # Use cached info if available
        if cached_info:
            logger.info(f"Using cached problem info for {problem_url}")
            update_progress("Loading from cache...")
            problem_info = cached_info
        else:
            # Use LLM service (Gemini or OpenAI) with 2-step extraction (metadata first, then solution)
            llm_service = LLMServiceFactory.create_service()

            # STEP 1: Extract problem metadata (title, constraints, samples)
            update_progress("📄 Step 1/2: Extracting problem metadata...")
            problem_metadata = llm_service.extract_problem_metadata_from_url(
                problem_url,
                progress_callback=lambda msg: update_progress(f"📄 {msg}")
            )
            logger.info(f"Extracted metadata: {problem_metadata['title']}, {len(problem_metadata.get('samples', []))} samples")

            # Update Problem with metadata immediately after extraction
            if job_id:
                try:
                    from api.dynamodb.client import DynamoDBClient
                    from api.dynamodb.repositories import ProblemRepository

                    table = DynamoDBClient.get_table()
                    problem_repo = ProblemRepository(table)

                    # Check if problem exists
                    existing_problem = problem_repo.get_problem(platform, problem_id)

                    if existing_problem:
                        # Update with metadata
                        metadata = {
                            **(existing_problem.get('metadata') or {}),
                            'extraction_job_id': job_id,
                            'extraction_status': 'PROCESSING',
                            'extracted_title': problem_metadata['title'],
                            'progress': f"Metadata extracted: {problem_metadata['title']}"
                        }

                        updates = {
                            'title': problem_metadata['title'],
                            'constraints': problem_metadata.get('constraints', ''),
                            'metadata': metadata
                        }
                        problem_repo.update_problem(platform, problem_id, updates)
                        logger.info(f"Updated problem {platform}/{problem_id} with metadata: {problem_metadata['title']}")
                    else:
                        # Create problem with metadata
                        metadata = {
                            'extraction_job_id': job_id,
                            'extraction_status': 'PROCESSING',
                            'extracted_title': problem_metadata['title'],
                            'progress': f"Metadata extracted: {problem_metadata['title']}"
                        }

                        problem_repo.create_problem(
                            platform=platform,
                            problem_id=problem_id,
                            problem_data={
                                'title': problem_metadata['title'],
                                'problem_url': problem_url,
                                'constraints': problem_metadata.get('constraints', ''),
                                'solution_code': '',  # Will be added in Step 2
                                'language': 'cpp',
                                'tags': [],
                                'is_completed': False,
                                'metadata': metadata
                            }
                        )
                        logger.info(f"Created problem {platform}/{problem_id} with metadata")

                except Exception as e:
                    logger.error(f"Failed to update problem with metadata: {e}")

            # STEP 2: Generate solution with Gemini → OpenAI fallback
            solution_result, validation_passed, validation_error, used_service = generate_solution_with_fallback(
                problem_metadata,
                update_progress
            )

            # Log which service was used
            logger.info(f"Solution generated using {used_service.upper() if used_service else 'unknown service'}")

            # Get sample info for logging
            samples = problem_metadata.get('samples', [])

            # Combine metadata and solution
            problem_info = {
                **problem_metadata,
                'solution_code': solution_result['solution_code'] if solution_result else '',
                'constraints': problem_metadata.get('constraints', '')
            }

            # Add validation info based on fallback function results
            if validation_error and not validation_passed:
                problem_info['validation_warning'] = f'Solution may be incorrect: {validation_error}'
                problem_info['validation_passed'] = False
                problem_info['needs_review'] = True  # Mark for manual review when validation fails
                logger.warning(f"⚠ Solution validation failed with {used_service} - marking problem as needs_review")
            elif validation_passed and samples:
                problem_info['validation_passed'] = True
                problem_info['needs_review'] = False  # Validation passed, no review needed
                logger.info(f"✓ Solution validation passed with {used_service}")

            # OPTIMIZATION: Cache the result
            cache.set(cache_key, problem_info, CACHE_TTL_LONG)

        # Update job with results if job_id provided
        if job_id:
            job = JobHelper.get_problem_extraction_job(job_id)
            if job:
                JobHelper.update_problem_extraction_job(job_id, {
                    'status': 'COMPLETED'
                })

                # Create or update Problem in DynamoDB
                from api.dynamodb.client import DynamoDBClient
                from api.dynamodb.repositories import ProblemRepository

                table = DynamoDBClient.get_table()
                problem_repo = ProblemRepository(table)

                # Check if problem exists
                existing_problem = problem_repo.get_problem(platform, problem_id)

                if existing_problem:
                    # Update existing problem with extracted data
                    metadata = {
                        **(existing_problem.get('metadata') or {}),
                        'extraction_job_id': job_id,
                        'extraction_status': 'COMPLETED',
                        'extracted_title': problem_info['title']
                    }

                    # Add validation warning if present
                    if 'validation_warning' in problem_info:
                        metadata['validation_warning'] = problem_info['validation_warning']
                        metadata['validation_passed'] = problem_info.get('validation_passed', False)
                        metadata['needs_review'] = problem_info.get('needs_review', False)

                    updates = {
                        'title': problem_info['title'],
                        'problem_url': problem_url,
                        'constraints': problem_info['constraints'],
                        'solution_code': problem_info['solution_code'],
                        'language': 'cpp',
                        'is_completed': False,  # Keep as draft
                        'metadata': metadata
                    }
                    problem_repo.update_problem(platform, problem_id, updates)
                    logger.info(f"Updated problem {platform}/{problem_id} with extracted title: {problem_info['title']}")
                    update_progress("Problem updated successfully", status='completed')
                    created = False
                else:
                    # Create new problem
                    metadata = {
                        'extraction_job_id': job_id,
                        'extraction_status': 'COMPLETED'
                    }

                    # Add validation warning if present
                    if 'validation_warning' in problem_info:
                        metadata['validation_warning'] = problem_info['validation_warning']
                        metadata['validation_passed'] = problem_info.get('validation_passed', False)
                        metadata['needs_review'] = problem_info.get('needs_review', False)

                    problem_repo.create_problem(
                        platform=platform,
                        problem_id=problem_id,
                        problem_data={
                            'title': problem_info['title'],
                            'problem_url': problem_url,
                            'constraints': problem_info['constraints'],
                            'solution_code': problem_info['solution_code'],
                            'language': 'cpp',
                            'tags': [],
                            'is_completed': False,  # Draft state
                            'metadata': metadata
                        }
                    )
                    logger.info(f"Created problem {platform}/{problem_id} in DynamoDB")
                    update_progress("Problem created successfully", status='completed')
                    created = True

                logger.info(f"Problem {platform}/{problem_id} {'created' if created else 'updated'} from job {job_id}")
            else:
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
            job = JobHelper.get_problem_extraction_job(job_id)
            if job:
                JobHelper.update_problem_extraction_job(job_id, {
                    'status': 'FAILED',
                    'error_message': str(e)
                })

                # Update Problem metadata to FAILED in DynamoDB and log to progress
                try:
                    from api.dynamodb.client import DynamoDBClient
                    from api.dynamodb.repositories import ProblemRepository

                    table = DynamoDBClient.get_table()
                    problem_repo = ProblemRepository(table)
                    problem = problem_repo.get_problem(job['platform'], job['problem_id'])
                    if problem:
                        updates = {
                            'metadata': {
                                **(problem.get('metadata') or {}),
                                'extraction_status': 'FAILED',
                                'extraction_job_id': job_id,
                                'extraction_error': str(e)
                            }
                        }
                        problem_repo.update_problem(job['platform'], job['problem_id'], updates)
                        logger.info(f"[Worker] Problem {job['platform']}/{job['problem_id']} status updated to FAILED")
                    else:
                        logger.warning(f"[Worker] Problem not found for {job['platform']}/{job['problem_id']}")
                except Exception as ex:
                    logger.warning(f"[Worker] Failed to update problem status: {ex}")
            else:
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
    acks_late=False,  # ACK immediately on consume to prevent duplicate execution
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_hints_task(self, history_id):
    """
    Async task to generate hints for a failed code execution - DynamoDB implementation

    OPTIMIZATIONS:
    - Uses DynamoDB SearchHistory repository for data access
    - Efficient field extraction with short names
    - Early validation and exit conditions
    - Cache hints to avoid regeneration

    Args:
        history_id: ID of the SearchHistory record

    Returns:
        dict: Result with status and hints
    """
    from api.dynamodb.client import DynamoDBClient
    from api.dynamodb.repositories import SearchHistoryRepository, ProblemRepository

    logger.info(f"[HINTS] Starting hint generation for history {history_id}")

    try:
        # Fetch history record from DynamoDB
        logger.info(f"[HINTS] Fetching history record {history_id} from DynamoDB")
        table = DynamoDBClient.get_table()
        history_repo = SearchHistoryRepository(table)
        history = history_repo.get_history(history_id)

        if not history:
            logger.error(f"[HINTS] History {history_id}: SearchHistory not found in DynamoDB")
            return {
                'status': 'FAILED',
                'error': 'Search history not found'
            }

        # Extract data from DynamoDB format (short field names)
        history_data = history.get('dat', {})
        failed_count = history_data.get('fsc', 0)  # failed_count
        hints = history_data.get('hnt')  # hints
        code = history_data.get('cod', '')  # code
        language = history_data.get('lng', '')  # language
        test_results = history_data.get('trs', [])  # test_results
        problem_composite = history_data.get('pid', '')  # problem composite key
        problem_title = history_data.get('ptt', '')  # problem_title
        platform = history_data.get('plt', '')  # platform

        logger.info(f"[HINTS] Retrieved history {history_id}: problem={problem_title}, failed_count={failed_count}, language={language}")

        # Early validation: Check if there are any failures
        if failed_count == 0:
            logger.info(f"History {history_id} has no failures, hints not needed")
            return {
                'status': 'FAILED',
                'error': 'No failed test cases - hints not needed'
            }

        # Early exit: Check if hints already exist
        if hints:
            logger.info(f"History {history_id} already has hints")
            return {
                'status': 'COMPLETED',
                'hints': hints,
                'message': 'Hints already exist'
            }

        # Parse problem composite key to get platform/problem_id
        parts = problem_composite.split('#')
        if len(parts) >= 2:
            problem_platform = parts[0]
            problem_number = '#'.join(parts[1:])
        else:
            problem_platform = platform
            problem_number = problem_composite

        # Get problem from DynamoDB to access solution code
        problem_repo = ProblemRepository(table)
        problem = problem_repo.get_problem(
            platform=problem_platform,
            problem_id=problem_number
        )

        if not problem:
            logger.warning(f"[HINTS] History {history_id} - problem not found in DynamoDB")
            return {
                'status': 'FAILED',
                'error': 'Problem not found'
            }

        # Validate problem has solution code
        solution_code = problem.get('solution_code', '')
        if not solution_code:
            logger.warning(f"History {history_id} - problem has no solution code")
            return {
                'status': 'FAILED',
                'error': 'No solution code available for this problem'
            }

        # Extract failed tests efficiently - convert from short field names to long names
        failed_tests = []
        for result in test_results:
            if not result.get('pas', True):  # pas = passed
                # Convert short names to long names for Gemini
                failed_tests.append({
                    'test_case_id': result.get('tid'),  # tid = test_case_id
                    'output': result.get('out', ''),  # out = output
                    'passed': result.get('pas', False),  # pas = passed
                    'error': result.get('err'),  # err = error
                    'status': result.get('sts', '')  # sts = status
                })

        if not failed_tests:
            logger.warning(f"[HINTS] History {history_id} has no failed test case details")
            return {
                'status': 'FAILED',
                'error': 'No failed test case details available'
            }

        logger.info(f"[HINTS] History {history_id}: Found {len(failed_tests)} failed tests")

        # Decode solution code (it's stored as base64)
        try:
            decoded_solution = base64.b64decode(solution_code).decode('utf-8')
            logger.info(f"[HINTS] History {history_id}: Successfully decoded solution code")
        except Exception as e:
            # If decoding fails, use as-is (for backwards compatibility)
            logger.warning(f"[HINTS] History {history_id}: Failed to decode solution code, using as-is: {e}")
            decoded_solution = solution_code

        # Prepare problem info
        problem_info = {
            'title': problem_title,
            'platform': problem_platform,
            'problem_id': problem_number,
            'language': language
        }

        # Generate hints using LLM service (Gemini or OpenAI based on settings)
        logger.info(f"[HINTS] History {history_id}: Calling LLM API to generate hints")
        llm_service = LLMServiceFactory.create_service()
        generated_hints = llm_service.generate_hints(
            user_code=code,
            solution_code=decoded_solution,
            test_failures=failed_tests,
            problem_info=problem_info
        )
        logger.info(f"[HINTS] History {history_id}: LLM API returned {len(generated_hints) if generated_hints else 0} hints")

        # Save hints to history record in DynamoDB
        logger.info(f"[HINTS] History {history_id}: Saving hints to DynamoDB")
        history_repo.update_hints(
            history_id=history_id,
            hints=generated_hints
        )
        logger.info(f"[HINTS] History {history_id}: Successfully saved {len(generated_hints)} hints to DynamoDB")

        logger.info(f"[HINTS] History {history_id}: Task completed successfully with {len(generated_hints)} hints")

        return {
            'status': 'COMPLETED',
            'hints': generated_hints,
            'message': f'Generated {len(generated_hints)} hints successfully'
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
    - Uses JobHelper for DynamoDB deletion
    - Ignore result to save space
    - Fast execution with minimal overhead

    Args:
        job_id: ID of the ScriptGenerationJob to delete

    Returns:
        dict: Result with job_id and status
    """
    try:
        # Delete the job from DynamoDB
        result = JobHelper.delete_script_generation_job(job_id)

        if result:
            logger.info(f"Deleted job {job_id}")
            return {
                'status': 'COMPLETED',
                'job_id': job_id,
                'message': f'Job {job_id} deleted successfully'
            }
        else:
            logger.error(f"Job {job_id} not found for deletion")
            return {
                'status': 'FAILED',
                'error': 'Job not found'
            }

    except Exception as e:
        logger.error(f"Error in delete_job_task for job {job_id}: {str(e)}", exc_info=True)
        # Don't retry - handled by autoretry_for
        raise


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    time_limit=120,  # 2 minutes hard limit
    soft_time_limit=100,  # 100 seconds soft limit
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    ignore_result=True,  # No need to store result for delete operations
)
def hard_delete_problem_task(self, platform, problem_id):
    """
    Async task to permanently delete a soft-deleted Problem from DynamoDB

    This task should only be called after a problem has been soft-deleted (is_deleted=True).
    It performs the actual hard deletion from DynamoDB.

    OPTIMIZATIONS:
    - Uses ProblemRepository for DynamoDB deletion
    - Ignore result to save space
    - Fast execution with minimal overhead
    - Invalidates related caches

    Args:
        platform: Platform name (e.g., 'baekjoon', 'codeforces')
        problem_id: Problem ID on the platform

    Returns:
        dict: Result with platform, problem_id and status
    """
    try:
        from .dynamodb.client import DynamoDBClient
        from .dynamodb.repositories import ProblemRepository

        # Initialize repository
        table = DynamoDBClient.get_table()
        problem_repo = ProblemRepository(table)

        # Verify problem exists and is soft-deleted
        problem = problem_repo.get_problem(platform=platform, problem_id=problem_id)

        if not problem:
            logger.warning(f"Problem {platform}/{problem_id} not found for hard deletion")
            return {
                'status': 'FAILED',
                'error': 'Problem not found'
            }

        if not problem.get('is_deleted', False):
            logger.warning(f"Problem {platform}/{problem_id} is not soft-deleted, refusing hard delete")
            return {
                'status': 'FAILED',
                'error': 'Problem is not soft-deleted'
            }

        # Perform hard delete
        success = problem_repo.delete_problem(platform=platform, problem_id=problem_id)

        if success:
            logger.info(f"Hard deleted problem {platform}/{problem_id}")

            # Invalidate related caches
            cache.delete("problem_drafts:all")
            cache.delete("problem_registered:all")
            cache.delete(f"problem:{platform}:{problem_id}")

            return {
                'status': 'COMPLETED',
                'platform': platform,
                'problem_id': problem_id,
                'message': f'Problem {platform}/{problem_id} permanently deleted'
            }
        else:
            logger.error(f"Failed to hard delete problem {platform}/{problem_id}")
            return {
                'status': 'FAILED',
                'error': 'Failed to delete from DynamoDB'
            }

    except Exception as e:
        logger.error(f"Error in hard_delete_problem_task for {platform}/{problem_id}: {str(e)}", exc_info=True)
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
        from api.dynamodb.repositories import ProblemRepository

        logger.info("Starting cache warming task for problems using DynamoDB...")

        problem_repo = ProblemRepository()
        ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)

        # 1. Warm cache for completed problems list (main endpoint)
        cache_key = CacheKeyGenerator.problem_list_key()
        completed_problems, _ = problem_repo.list_completed_problems(limit=1000)
        cache.set(cache_key, completed_problems, ttl)
        logger.info(f"Warmed cache: {cache_key} ({len(completed_problems)} problems)")

        # 2. Warm cache for registered problems endpoint
        cache_key = "problem_registered:all"
        cache.set(cache_key, {'problems': completed_problems}, ttl)
        logger.info(f"Warmed cache: {cache_key}")

        # 3. Warm cache for platform-specific problem lists
        # Group by platform
        platforms_dict = {}
        for problem in completed_problems:
            platform = problem.get('platform')
            if platform not in platforms_dict:
                platforms_dict[platform] = []
            platforms_dict[platform].append(problem)

        for platform, problems in platforms_dict.items():
            cache_key = CacheKeyGenerator.problem_list_key(platform=platform)
            cache.set(cache_key, problems, ttl)
            logger.info(f"Warmed cache: {cache_key} ({len(problems)} problems)")

        # 4. Warm cache for most recently accessed problem details (top 20)
        ttl_detail = settings.CACHE_TTL.get('PROBLEM_DETAIL', 600)
        recent_count = min(20, len(completed_problems))
        for idx, problem in enumerate(completed_problems[:recent_count]):
            # Get full problem with test cases
            problem_with_tests = problem_repo.get_problem_with_testcases(
                platform=problem['platform'],
                problem_id=problem['problem_id']
            )
            if problem_with_tests:
                # Note: problem_id here is platform#problem_id key, need to derive actual cache key
                cache_key = f"problem_detail:{problem['platform']}:{problem['problem_id']}"
                cache.set(cache_key, problem_with_tests, ttl_detail)

        logger.info(f"Warmed cache for {recent_count} problem details")

        # 5. Warm cache for draft problems
        cache_key = "problem_drafts:all"
        draft_problems, _ = problem_repo.list_draft_problems(limit=1000)
        ttl_short = settings.CACHE_TTL.get('SHORT', 60)
        cache.set(cache_key, {'drafts': draft_problems}, ttl_short)
        logger.info(f"Warmed cache: {cache_key} ({len(draft_problems)} drafts)")

        logger.info("Cache warming task completed successfully")
        return {'status': 'SUCCESS', 'message': 'Problem cache warmed successfully'}

    except Exception as e:
        logger.error(f"Error in warm_problem_cache_task: {str(e)}", exc_info=True)
        raise


# REMOVED: warm_user_stats_cache_task - requires ORM migration to DynamoDB
# TODO: Re-implement using SearchHistoryRepository with DynamoDB aggregations


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
        import time
        cutoff_timestamp = time.time() - (timeout_minutes * 60)

        # Find orphaned extraction jobs from DynamoDB
        orphaned_extraction, _ = JobHelper.list_problem_extraction_jobs(status='PROCESSING', limit=1000)
        orphaned_extraction = [job for job in orphaned_extraction if job.get('updated_at', 0) < cutoff_timestamp]

        # Find orphaned generation jobs from DynamoDB
        orphaned_generation, _ = JobHelper.list_script_generation_jobs(status='PROCESSING', limit=1000)
        orphaned_generation = [job for job in orphaned_generation if job.get('updated_at', 0) < cutoff_timestamp]

        extraction_count = len(orphaned_extraction)
        generation_count = len(orphaned_generation)
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

        from api.dynamodb.client import DynamoDBClient
        from api.dynamodb.repositories import ProblemRepository

        table = DynamoDBClient.get_table()
        problem_repo = ProblemRepository(table)

        for job in orphaned_extraction:
            job_id = job['job_id']
            platform = job['platform']
            problem_id = job['problem_id']

            try:
                # Check if Problem exists in DynamoDB
                problem = problem_repo.get_problem(platform, problem_id)

                if problem:
                    # Problem exists - mark job as FAILED
                    JobHelper.update_problem_extraction_job(job_id, {
                        'status': 'FAILED',
                        'error_message': f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
                    })
                    failed_count += 1

                    # Update Problem metadata
                    problem_repo.update_problem(platform, problem_id, {
                        'metadata': {
                            **(problem.get('metadata') or {}),
                            'extraction_status': 'FAILED',
                            'extraction_job_id': job_id,
                            'error_message': 'Job orphaned and automatically recovered'
                        }
                    })
                    updated_problems += 1
                    logger.info(f"[Orphaned Job Recovery] Marked job #{job_id} as FAILED and updated Problem {platform}/{problem_id}")
                else:
                    # Problem doesn't exist - delete the job
                    JobHelper.delete_problem_extraction_job(job_id)
                    deleted_count += 1
                    logger.info(f"[Orphaned Job Recovery] Deleted orphaned job #{job_id} (Problem {platform}/{problem_id} not found)")

            except Exception as e:
                logger.error(f"[Orphaned Job Recovery] Error processing extraction job {job_id}: {e}")

        # Mark generation jobs as failed
        updated_generation = 0
        for job in orphaned_generation:
            try:
                JobHelper.update_script_generation_job(job['job_id'], {
                    'status': 'FAILED',
                    'error_message': f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
                })
                updated_generation += 1
            except Exception as e:
                logger.error(f"[Orphaned Job Recovery] Error updating generation job {job['job_id']}: {e}")

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
