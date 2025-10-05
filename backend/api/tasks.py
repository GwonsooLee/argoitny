"""Celery tasks for async processing"""
from celery import shared_task
from django.db import models, transaction
from .models import ScriptGenerationJob, Problem, TestCase, SearchHistory, User
from .services.gemini_service import GeminiService
from .services.code_execution_service import CodeExecutionService
import base64


@shared_task(bind=True, max_retries=3)
def generate_script_task(self, job_id):
    """
    Async task to generate test case generator script using Gemini AI

    Args:
        job_id: ID of the ScriptGenerationJob

    Returns:
        dict: Result with job_id and status
    """
    try:
        # Get the job
        job = ScriptGenerationJob.objects.get(id=job_id)

        # Update status to PROCESSING
        job.status = 'PROCESSING'
        job.celery_task_id = self.request.id
        job.save()

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

        # Generate script using Gemini
        gemini_service = GeminiService()
        generator_code = gemini_service.generate_test_case_generator_code(problem_info)

        # Update job with result
        job.status = 'COMPLETED'
        job.generator_code = generator_code
        job.save()

        # Execute generator code to create test cases and save to Problem
        try:
            from .services.test_case_generator import TestCaseGenerator
            from .models import TestCase
            from django.db import transaction

            # Generate test cases using the script
            test_case_inputs = TestCaseGenerator.execute_generator_code(
                code=generator_code,
                num_cases=20
            )

            # Get or create the problem
            problem, created = Problem.objects.get_or_create(
                platform=job.platform,
                problem_id=job.problem_id,
                defaults={
                    'title': job.title,
                    'problem_url': job.problem_url or '',
                    'tags': job.tags or [],
                    'solution_code': job.solution_code or '',
                    'language': job.language,
                    'constraints': job.constraints
                }
            )

            # If problem exists, update it
            if not created:
                problem.title = job.title
                problem.problem_url = job.problem_url or ''
                problem.tags = job.tags or []
                problem.solution_code = job.solution_code or ''
                problem.language = job.language
                problem.constraints = job.constraints
                problem.save()

            # Delete existing test cases for this problem first
            with transaction.atomic():
                TestCase.objects.filter(problem=problem).delete()

                # Execute solution code with generated inputs to get outputs
                if job.solution_code:
                    from .services.code_execution_service import CodeExecutionService

                    test_results = CodeExecutionService.execute_with_test_cases(
                        code=job.solution_code,
                        language=job.language,
                        test_inputs=test_case_inputs
                    )

                    # Create new test cases with outputs
                    test_case_objects = [
                        TestCase(
                            problem=problem,
                            input=r['input'],
                            output=r['output']
                        )
                        for r in test_results if r['status'] == 'success'
                    ]
                    TestCase.objects.bulk_create(test_case_objects)
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
                    TestCase.objects.bulk_create(test_case_objects)

        except Exception as e:
            # Log but don't fail the task if test case generation fails
            print(f"Warning: Failed to generate/save test cases: {str(e)}")

        return {
            'job_id': job_id,
            'status': 'COMPLETED',
            'message': 'Script generated successfully'
        }

    except ScriptGenerationJob.DoesNotExist:
        return {
            'job_id': job_id,
            'status': 'FAILED',
            'error': 'Job not found'
        }

    except Exception as e:
        # Update job with error
        try:
            job = ScriptGenerationJob.objects.get(id=job_id)
            job.status = 'FAILED'
            job.error_message = str(e)
            job.save()
        except:
            pass

        # Retry the task if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

        return {
            'job_id': job_id,
            'status': 'FAILED',
            'error': str(e)
        }


@shared_task(bind=True, max_retries=3)
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
        # Get the problem with test cases
        problem = Problem.objects.prefetch_related('test_cases').get(
            platform=platform,
            problem_id=problem_id
        )

        if not problem.solution_code:
            return {
                'status': 'FAILED',
                'error': 'Problem has no solution code'
            }

        test_cases = problem.test_cases.all()
        if not test_cases:
            return {
                'status': 'FAILED',
                'error': 'Problem has no test cases'
            }

        # Get test inputs
        test_inputs = [tc.input for tc in test_cases]

        # Decode base64 solution code before executing
        decoded_code = base64.b64decode(problem.solution_code).decode('utf-8')

        # Execute solution code with test inputs
        test_results = CodeExecutionService.execute_with_test_cases(
            code=decoded_code,
            language=problem.language or 'python',
            test_inputs=test_inputs
        )

        # Update test cases with outputs
        with transaction.atomic():
            for tc, result in zip(test_cases, test_results):
                if result['status'] == 'success':
                    tc.output = result['output']
                    tc.save()

        success_count = len([r for r in test_results if r['status'] == 'success'])

        return {
            'status': 'COMPLETED',
            'count': success_count,
            'message': f'Outputs generated successfully for {success_count} test cases'
        }

    except Problem.DoesNotExist:
        return {
            'status': 'FAILED',
            'error': 'Problem not found'
        }

    except Exception as e:
        # Retry the task if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

        return {
            'status': 'FAILED',
            'error': str(e)
        }


@shared_task(bind=True, max_retries=3)
def execute_code_task(self, code, language, problem_id, user_id, user_identifier, is_code_public):
    """
    Async task to execute code against test cases

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
        # Get problem with test cases
        problem = Problem.objects.prefetch_related('test_cases').get(id=problem_id)

        if not problem.test_cases.exists():
            return {
                'status': 'FAILED',
                'error': 'No test cases available for this problem'
            }

        # Get test cases
        test_cases = problem.test_cases.all()
        test_inputs = [tc.input for tc in test_cases]

        # Execute code
        test_results = CodeExecutionService.execute_with_test_cases(
            code=code,
            language=language,
            test_inputs=test_inputs
        )

        # Build results for frontend (with input and expected)
        results = []
        # Build history results for database (without input and expected)
        history_results = []
        passed_count = 0
        failed_count = 0

        for tc, result in zip(test_cases, test_results):
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

            # For database - only output
            history_results.append({
                'test_case_id': tc.id,
                'output': result.get('output', ''),
                'passed': passed,
                'error': result.get('error'),
                'status': result['status']
            })

        # Save to search history
        try:
            user = None
            if user_id:
                user = User.objects.filter(id=user_id).first()

            SearchHistory.objects.create(
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

            # Update problem execution count in metadata
            if not problem.metadata:
                problem.metadata = {}
            problem.metadata['execution_count'] = problem.metadata.get('execution_count', 0) + 1
            problem.save()
        except Exception as e:
            print(f"Failed to save search history: {str(e)}")

        return {
            'status': 'COMPLETED',
            'results': results,
            'summary': {
                'total': len(test_cases),
                'passed': passed_count,
                'failed': failed_count
            }
        }

    except Problem.DoesNotExist:
        return {
            'status': 'FAILED',
            'error': 'Problem not found'
        }
    except Exception as e:
        # Retry the task if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)

        return {
            'status': 'FAILED',
            'error': str(e)
        }
