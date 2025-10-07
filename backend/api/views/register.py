"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from ..models import Problem, TestCase, ScriptGenerationJob, ProblemExtractionJob
from ..services.gemini_service import GeminiService
from ..services.code_executor import CodeExecutor
from ..services.test_case_generator import TestCaseGenerator
from ..services.code_execution_service import CodeExecutionService
from ..serializers import (
    ProblemRegisterSerializer,
    GenerateTestCasesSerializer,
    ProblemSerializer,
    ProblemSaveSerializer,
    ScriptGenerationJobSerializer,
    ExtractProblemInfoSerializer
)
from ..tasks import generate_script_task, extract_problem_info_task
import logging

logger = logging.getLogger(__name__)


class GenerateTestCasesView(APIView):
    """Generate test case generator code using Gemini AI"""
    permission_classes = [AllowAny]  # Allow for development

    def post(self, request):
        # Check if user is authenticated and has permission
        if request.user and request.user.is_authenticated:
            if not request.user.is_staff:
                limits = request.user.get_plan_limits()
                if not limits.get('can_register_problems', False):
                    return Response(
                        {'error': 'You do not have permission to register problems'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        """
        Enqueue a job to generate Python code that will generate test cases using Gemini AI

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "problem_url": "https://www.acmicpc.net/problem/1000",  # Optional
                "tags": ["math", "implementation"],  # Optional
                "solution_code": "a, b = map(int, input().split())\nprint(a + b)",  # Optional
                "language": "python",
                "constraints": "1 <= a, b <= 10"
            }

        Returns:
            {
                "job_id": 1,
                "status": "PENDING",
                "message": "Job created and queued for processing"
            }
        """
        serializer = GenerateTestCasesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create a job record
            job = ScriptGenerationJob.objects.create(
                platform=serializer.validated_data['platform'],
                problem_id=serializer.validated_data['problem_id'],
                title=serializer.validated_data['title'],
                problem_url=serializer.validated_data.get('problem_url', ''),
                tags=serializer.validated_data.get('tags', []),
                solution_code=serializer.validated_data.get('solution_code', ''),
                language=serializer.validated_data['language'],
                constraints=serializer.validated_data['constraints'],
                status='PENDING'
            )

            # Enqueue the job to Celery
            task = generate_script_task.delay(job.id)

            # Update job with task ID (optimized: use update_fields)
            job.celery_task_id = task.id
            job.save(update_fields=['celery_task_id'])

            return Response({
                'job_id': job.id,
                'status': job.status,
                'message': 'Job created and queued for processing'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response(
                {'error': f'Failed to create job: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterProblemView(APIView):
    """Register problem with test cases"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if user has permission to register problems
        if not request.user.is_admin():
            limits = request.user.get_plan_limits()
            if not limits.get('can_register_problems', False):
                return Response(
                    {'error': 'You do not have permission to register problems'},
                    status=status.HTTP_403_FORBIDDEN
                )
        """
        Register problem with test cases

        Request body:
            {
                "platform": "baekjoon",  # Optional if problem_url provided
                "problem_id": "1000",  # Optional if problem_url provided
                "title": "A+B",
                "problem_url": "https://www.acmicpc.net/problem/1000",  # Optional
                "tags": ["math", "implementation"],  # Optional
                "solution_code": "a, b = map(int, input().split())\\nprint(a + b)",
                "language": "python",
                "constraints": "1 <= a, b <= 10"
            }

        Returns:
            {
                "message": "Problem registered successfully",
                "problem": {
                    "id": 1,
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "problem_url": "https://www.acmicpc.net/problem/1000",
                    "tags": ["math", "implementation"],
                    "created_at": "...",
                    "test_cases": [
                        {
                            "id": 1,
                            "input": "1 2",
                            "output": "3"
                        },
                        ...
                    ]
                }
            }
        """
        serializer = ProblemRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        platform = serializer.validated_data['platform']
        problem_id = serializer.validated_data['problem_id']
        title = serializer.validated_data['title']
        problem_url = serializer.validated_data.get('problem_url')
        tags = serializer.validated_data.get('tags', [])
        solution_code = serializer.validated_data['solution_code']
        language = serializer.validated_data['language']

        try:
            # Check if problem already exists (optimized: use only() to fetch minimal data)
            if Problem.objects.filter(platform=platform, problem_id=problem_id).only('id').exists():
                return Response(
                    {'error': 'Problem already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get test case inputs from request (generated from job)
            test_case_inputs = request.data.get('test_case_inputs', [])
            if not test_case_inputs:
                return Response(
                    {'error': 'test_case_inputs is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Use CodeExecutionService (Judge0 or local based on config)
            test_results = CodeExecutionService.execute_with_test_cases(
                code=solution_code,
                language=language,
                test_inputs=test_case_inputs
            )

            # Check if all test cases executed successfully
            failed_tests = [r for r in test_results if r['status'] == 'error']
            if failed_tests:
                return Response(
                    {
                        'error': 'Some test cases failed to execute',
                        'failed_tests': failed_tests
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prepare test cases with outputs
            test_cases_with_outputs = [
                {'input': r['input'], 'output': r['output']}
                for r in test_results
            ]

            # Save problem and test cases
            with transaction.atomic():
                problem = Problem.objects.create(
                    platform=platform,
                    problem_id=problem_id,
                    title=title,
                    problem_url=problem_url,
                    tags=tags
                )

                # Bulk create test cases
                test_case_objects = [
                    TestCase(
                        problem=problem,
                        input=tc['input'],
                        output=tc['output']
                    )
                    for tc in test_cases_with_outputs
                ]
                TestCase.objects.bulk_create(test_case_objects)

            # Fetch problem with test cases for response
            problem = Problem.objects.prefetch_related('test_cases').get(id=problem.id)
            problem_serializer = ProblemSerializer(problem)

            return Response({
                'message': 'Problem registered successfully',
                'problem': problem_serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to register problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExecuteTestCasesView(APIView):
    """Execute generator code to produce test cases"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Execute test case generator code to produce test case inputs

        Request body:
            {
                "generator_code": "def generate_test_cases(n):...",
                "num_cases": 10
            }

        Returns:
            {
                "test_cases": ["1 2", "3 4", ...]
            }
        """
        generator_code = request.data.get('generator_code')
        num_cases = request.data.get('num_cases', 10)

        if not generator_code:
            return Response(
                {'error': 'generator_code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            num_cases = int(num_cases)
            if num_cases < 1 or num_cases > 1000:
                return Response(
                    {'error': 'num_cases must be between 1 and 1000'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'num_cases must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Execute the generator code
            test_cases = TestCaseGenerator.execute_generator_code(
                code=generator_code,
                num_cases=num_cases
            )

            return Response({
                'test_cases': test_cases,
                'count': len(test_cases)
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to execute generator code: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DraftProblemsView(APIView):
    """Get list of draft problems (problems without test cases)"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all draft problems (is_completed=False)

        Returns:
            {
                "drafts": [
                    {
                        "id": 1,
                        "platform": "baekjoon",
                        "problem_id": "1000",
                        "title": "A+B",
                        "problem_url": "https://...",
                        "tags": ["math"],
                        "created_at": "..."
                    },
                    ...
                ]
            }
        """
        try:
            # OPTIMIZATION: Use only() to fetch only needed fields
            # This reduces data transfer from database significantly
            drafts = Problem.objects.only(
                'id', 'platform', 'problem_id', 'title', 'problem_url',
                'tags', 'solution_code', 'language', 'constraints', 'created_at', 'metadata'
            ).filter(is_completed=False).order_by('-created_at')

            # OPTIMIZATION: Process in Python to decode base64 (consider moving to serializer)
            import base64
            draft_data = []
            for problem in drafts:
                # Decode solution_code from base64
                solution_code = problem.solution_code or ''
                if solution_code:
                    try:
                        solution_code = base64.b64decode(solution_code).decode('utf-8')
                    except:
                        # If decoding fails, use as-is
                        pass

                # Get extraction job status if available
                extraction_status = problem.metadata.get('extraction_status') if problem.metadata else None
                extraction_job_id = problem.metadata.get('extraction_job_id') if problem.metadata else None

                draft_data.append({
                    'id': problem.id,
                    'platform': problem.platform,
                    'problem_id': problem.problem_id,
                    'title': problem.title,
                    'problem_url': problem.problem_url or '',
                    'tags': problem.tags or [],
                    'solution_code': solution_code,
                    'language': problem.language or 'python',
                    'constraints': problem.constraints or '',
                    'created_at': problem.created_at.isoformat(),
                    'extraction_status': extraction_status,
                    'extraction_job_id': extraction_job_id,
                })

            # Also include extraction jobs that haven't created Problems yet
            pending_jobs = ProblemExtractionJob.objects.filter(
                status__in=['PENDING', 'PROCESSING']
            ).order_by('-created_at')

            # Get job IDs that are already in draft_data
            existing_job_ids = {d.get('extraction_job_id') for d in draft_data if d.get('extraction_job_id')}

            # Add jobs that don't have corresponding Problems yet
            for job in pending_jobs:
                if job.id not in existing_job_ids:
                    draft_data.append({
                        'id': None,  # No Problem ID yet
                        'platform': job.platform or 'unknown',
                        'problem_id': job.problem_id or 'extracting',
                        'title': job.title or 'Extracting problem info...',
                        'problem_url': job.problem_url or '',
                        'tags': [],
                        'solution_code': '',
                        'language': 'cpp',
                        'constraints': '',
                        'created_at': job.created_at.isoformat(),
                        'extraction_status': job.status,
                        'extraction_job_id': job.id,
                        'is_extracting': True,  # Flag to indicate this is still being extracted
                    })

            # Re-sort by created_at after adding pending jobs
            draft_data.sort(key=lambda x: x['created_at'], reverse=True)

            return Response({
                'drafts': draft_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch drafts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobListView(APIView):
    """List all script generation jobs"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all script generation jobs, ordered by creation date (newest first)

        Query params:
            status: Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)
            platform: Filter by platform
            problem_id: Filter by problem_id

        Returns:
            {
                "jobs": [
                    {
                        "id": 1,
                        "platform": "baekjoon",
                        "problem_id": "1000",
                        "title": "A+B",
                        "status": "COMPLETED",
                        "generator_code": "...",
                        "created_at": "...",
                        ...
                    },
                    ...
                ]
            }
        """
        try:
            # OPTIMIZATION: Use only() to fetch only needed fields for list view
            # This significantly reduces data transfer, especially for generator_code field
            jobs = ScriptGenerationJob.objects.only(
                'id', 'platform', 'problem_id', 'title', 'problem_url', 'tags',
                'language', 'status', 'celery_task_id',
                'created_at', 'updated_at', 'error_message'
            )

            # Filter by status if provided - uses sgj_status_created_idx composite index
            status_filter = request.query_params.get('status')
            if status_filter:
                jobs = jobs.filter(status=status_filter.upper())

            # Filter by platform if provided - uses sgj_platform_problem_idx composite index
            platform = request.query_params.get('platform')
            if platform:
                jobs = jobs.filter(platform=platform)

            # Filter by problem_id if provided
            problem_id = request.query_params.get('problem_id')
            if problem_id:
                jobs = jobs.filter(problem_id=problem_id)

            # OPTIMIZATION: Order by created_at (uses existing model ordering)
            # Combined with filters, this uses composite indexes efficiently

            serializer = ScriptGenerationJobSerializer(jobs, many=True)

            return Response({
                'jobs': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch jobs: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobDetailView(APIView):
    """Get details of a specific job"""
    permission_classes = [AllowAny]

    def get(self, request, job_id):
        """
        Get details of a specific job

        Returns:
            {
                "id": 1,
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "status": "COMPLETED",
                "generator_code": "...",
                "error_message": null,
                "created_at": "...",
                "updated_at": "..."
            }
        """
        try:
            job = ScriptGenerationJob.objects.get(id=job_id)
            serializer = ScriptGenerationJobSerializer(job)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ScriptGenerationJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch job: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, job_id):
        """
        Delete a specific job synchronously

        Returns:
            {
                "message": "Job deleted successfully"
            }
        """
        try:
            # Get and delete the job
            job = ScriptGenerationJob.objects.only('id').get(id=job_id)
            job.delete()

            return Response({
                'message': 'Job deleted successfully'
            }, status=status.HTTP_200_OK)

        except ScriptGenerationJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete job: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RetryExtractionView(APIView):
    """Retry a failed problem extraction job"""
    permission_classes = [AllowAny]

    def post(self, request, job_id):
        """
        Retry a failed extraction job

        Returns:
            {
                "message": "Extraction job retry initiated",
                "job_id": 123,
                "status": "PENDING"
            }
        """
        try:
            # Get the job
            job = ProblemExtractionJob.objects.get(id=job_id)

            # Check if job is in a retry-able state (FAILED or PROCESSING - to allow cancellation and retry)
            if job.status not in ['FAILED', 'PROCESSING']:
                return Response(
                    {'error': f'Job status is {job.status}. Only FAILED or PROCESSING jobs can be retried.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the problem URL
            if not job.problem_url:
                return Response(
                    {'error': 'Job does not have a problem_url to retry'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reset job status and update Problem metadata atomically
            job.status = 'PENDING'
            job.error_message = None
            job.save()

            # Update Problem metadata to reflect retry
            try:
                problem = Problem.objects.get(
                    platform=job.platform,
                    problem_id=job.problem_id
                )
                problem.metadata = {
                    **(problem.metadata or {}),
                    'extraction_status': 'PENDING',
                    'extraction_job_id': job.id,
                    'progress': 'Retry initiated...',
                    'error_message': None
                }
                problem.save(update_fields=['metadata'])
                logger.info(f"Updated Problem {job.platform}/{job.problem_id} to PENDING")
            except Problem.DoesNotExist:
                logger.warning(f"Problem {job.platform}/{job.problem_id} not found")

            # Trigger the extraction task again
            from ..tasks import extract_problem_info_task
            extract_problem_info_task.apply_async(
                kwargs={
                    'problem_url': job.problem_url,
                    'job_id': job.id
                },
                queue='ai'
            )

            return Response({
                'message': 'Extraction job retry initiated',
                'job_id': job.id,
                'status': 'PENDING'
            }, status=status.HTTP_200_OK)

        except ScriptGenerationJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to retry job: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SaveTestCaseInputsView(APIView):
    """Save test case inputs to problem (without outputs)"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Save test case inputs to a problem

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "test_inputs": ["1 2", "3 4", ...]
            }

        Returns:
            {
                "message": "Test cases saved successfully",
                "count": 10
            }
        """
        platform = request.data.get('platform')
        problem_id = request.data.get('problem_id')
        test_inputs = request.data.get('test_inputs', [])

        if not platform or not problem_id:
            return Response(
                {'error': 'platform and problem_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not test_inputs:
            return Response(
                {'error': 'test_inputs is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the problem (optimized: only fetch id for filter)
            problem = Problem.objects.only('id').get(platform=platform, problem_id=problem_id)

            # Delete existing test cases
            with transaction.atomic():
                TestCase.objects.filter(problem=problem).delete()

                # Create new test cases with empty outputs
                test_case_objects = [
                    TestCase(
                        problem=problem,
                        input=inp,
                        output=''  # Empty output for now
                    )
                    for inp in test_inputs
                ]
                TestCase.objects.bulk_create(test_case_objects)

            return Response({
                'message': 'Test cases saved successfully',
                'count': len(test_inputs)
            }, status=status.HTTP_200_OK)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to save test cases: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateOutputsView(APIView):
    """Generate outputs for existing test case inputs (async)"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Generate outputs for test cases using solution code (async task)

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000"
            }

        Returns:
            {
                "message": "Output generation task started",
                "task_id": "abc123..."
            }
        """
        platform = request.data.get('platform')
        problem_id = request.data.get('problem_id')

        if not platform or not problem_id:
            return Response(
                {'error': 'platform and problem_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify problem exists and has solution code
            problem = Problem.objects.prefetch_related('test_cases').get(
                platform=platform,
                problem_id=problem_id
            )

            if not problem.solution_code:
                return Response(
                    {'error': 'Problem has no solution code'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            test_cases = problem.test_cases.all()
            if not test_cases:
                return Response(
                    {'error': 'Problem has no test cases'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start async task
            from api.tasks import generate_outputs_task
            task = generate_outputs_task.delay(platform, problem_id)

            return Response({
                'message': 'Output generation task started',
                'task_id': task.id
            }, status=status.HTTP_202_ACCEPTED)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to start output generation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckTaskStatusView(APIView):
    """Check the status of an async task"""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """
        Check the status of a Celery task

        Returns:
            {
                "status": "PENDING|PROCESSING|COMPLETED|FAILED",
                "result": {...} or "error": "..."
            }
        """
        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {
                'status': 'PENDING',
                'message': 'Task is waiting to be executed'
            }
        elif task.state == 'PROCESSING':
            response = {
                'status': 'PROCESSING',
                'message': 'Task is being processed'
            }
        elif task.state == 'PROGRESS':
            # Handle progress updates from task
            response = {
                'status': 'PROGRESS',
                'result': task.info if task.info else {}
            }
        elif task.state == 'SUCCESS':
            response = {
                'status': 'COMPLETED',
                'result': task.result
            }
        elif task.state == 'FAILURE':
            response = {
                'status': 'FAILED',
                'error': str(task.info)
            }
        else:
            response = {
                'status': task.state,
                'message': str(task.info)
            }

        return Response(response, status=status.HTTP_200_OK)


class ToggleCompletionView(APIView):
    """Toggle problem completion status"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Toggle problem completion status

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "is_completed": true/false
            }

        Returns:
            {
                "message": "Problem marked as completed/draft",
                "is_completed": true/false
            }
        """
        platform = request.data.get('platform')
        problem_id = request.data.get('problem_id')
        is_completed = request.data.get('is_completed')

        if not platform or not problem_id or is_completed is None:
            return Response(
                {'error': 'platform, problem_id, and is_completed are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert to boolean if it's a string
        if isinstance(is_completed, str):
            is_completed = is_completed.lower() in ('true', '1', 'yes')
        else:
            is_completed = bool(is_completed)

        try:
            problem = Problem.objects.only('id', 'is_completed').get(platform=platform, problem_id=problem_id)
            problem.is_completed = is_completed
            problem.save(update_fields=['is_completed'])

            message = 'Problem marked as completed' if is_completed else 'Problem marked as draft'
            return Response({
                'message': message,
                'is_completed': bool(problem.is_completed)
            }, status=status.HTTP_200_OK)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update completion status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SaveProblemView(APIView):
    """Save problem draft without test cases"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Save problem draft (without test case generation)

        Request body:
            {
                "platform": "baekjoon",  # Optional if problem_url provided
                "problem_id": "1000",  # Optional if problem_url provided
                "title": "A+B",
                "problem_url": "https://www.acmicpc.net/problem/1000",  # Optional
                "tags": ["math", "implementation"]  # Optional
            }

        Returns:
            {
                "message": "Problem saved successfully",
                "problem": {
                    "id": 1,
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "problem_url": "https://www.acmicpc.net/problem/1000",
                    "tags": ["math", "implementation"]
                }
            }
        """
        # Check if updating existing draft by ID
        draft_id = request.data.get('id')

        if draft_id:
            # Update existing draft by ID
            try:
                existing_problem = Problem.objects.get(id=draft_id)
                serializer = ProblemSaveSerializer(existing_problem, data=request.data, partial=True)
                if not serializer.is_valid():
                    return Response(
                        {'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                serializer.save()
                problem = existing_problem
            except Problem.DoesNotExist:
                return Response(
                    {'error': 'Draft not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Create new or update by platform + problem_id
            platform = request.data.get('platform')
            problem_id = request.data.get('problem_id')

            if not platform or not problem_id:
                return Response(
                    {'error': 'platform and problem_id are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if problem already exists
            try:
                existing_problem = Problem.objects.get(platform=platform, problem_id=problem_id)
                # Update existing problem (partial update)
                serializer = ProblemSaveSerializer(existing_problem, data=request.data, partial=True)
                if not serializer.is_valid():
                    return Response(
                        {'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                serializer.save()
                problem = existing_problem
            except Problem.DoesNotExist:
                # Create new problem
                serializer = ProblemSaveSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response(
                        {'error': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                problem = serializer.save()

        # Serialize response
        response_serializer = ProblemSaveSerializer(problem)

        return Response({
            'message': 'Problem saved successfully',
            'problem': response_serializer.data
        }, status=status.HTTP_200_OK)


class ExtractProblemInfoView(APIView):
    """Extract problem information from URL using Gemini AI"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Extract problem information from a problem URL (async)

        Request body:
            {
                "problem_url": "https://www.acmicpc.net/problem/1000"
            }

        Returns:
            {
                "problem_id": 123,
                "job_id": 1,
                "status": "PENDING",
                "message": "Problem draft created and extraction job queued"
            }
        """
        serializer = ExtractProblemInfoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        problem_url = serializer.validated_data['problem_url']

        # Add logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ExtractProblemInfoView] Received URL: {problem_url}")

        try:
            # Parse URL to extract platform and problem_id
            from ..utils.url_parser import ProblemURLParser
            platform, problem_id = ProblemURLParser.parse_url(problem_url)

            if not platform or not problem_id:
                return Response(
                    {'error': 'Could not parse problem URL. Supported platforms: Baekjoon, Codeforces'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"[ExtractProblemInfoView] Parsed URL: platform={platform}, problem_id={problem_id}")

            # Create Problem immediately as draft
            problem, created = Problem.objects.get_or_create(
                platform=platform,
                problem_id=problem_id,
                defaults={
                    'title': f'{platform.upper()} {problem_id}',  # Use problem identifier as title
                    'problem_url': problem_url,
                    'constraints': '',
                    'solution_code': '',
                    'language': 'cpp',
                    'tags': [],
                    'is_completed': False,
                    'metadata': {
                        'extraction_status': 'PENDING'
                    }
                }
            )

            logger.info(f"[ExtractProblemInfoView] {'Created' if created else 'Found existing'} Problem with ID: {problem.id}")

            # If problem already exists, check if we should create a new job
            if not created:
                # Get extraction status
                extraction_status = problem.metadata.get('extraction_status') if problem.metadata else None

                # If extraction is completed or problem is marked as completed, don't create new job
                if extraction_status == 'COMPLETED' or problem.is_completed or problem.constraints:
                    logger.info(f"[ExtractProblemInfoView] Problem already fully extracted. extraction_status={extraction_status}, is_completed={problem.is_completed}")
                    return Response({
                        'problem_id': problem.id,
                        'platform': problem.platform,
                        'problem_identifier': problem.problem_id,
                        'job_id': None,
                        'status': 'COMPLETED',
                        'message': 'This problem has already been registered and extraction is complete. View your problem below.',
                        'already_exists': True
                    }, status=status.HTTP_200_OK)

                # If extraction is in progress or pending, return existing job info
                if extraction_status in ['PROCESSING', 'PENDING']:
                    existing_job_id = problem.metadata.get('extraction_job_id')
                    if existing_job_id:
                        try:
                            existing_job = ScriptGenerationJob.objects.get(id=existing_job_id)
                            logger.info(f"[ExtractProblemInfoView] Found existing job {existing_job.id} with status {existing_job.status}")

                            # Return existing draft info without creating new job
                            return Response({
                                'problem_id': problem.id,
                                'platform': problem.platform,
                                'problem_identifier': problem.problem_id,
                                'job_id': existing_job.id,
                                'status': existing_job.status,
                                'message': f'Problem extraction is already in progress. Current status: {existing_job.status}. View your draft below.',
                                'already_exists': True
                            }, status=status.HTTP_200_OK)
                        except ScriptGenerationJob.DoesNotExist:
                            logger.info(f"[ExtractProblemInfoView] Job {existing_job_id} not found, creating new job")
                            pass  # Job was deleted, create a new one

                # If extraction failed, allow retry by creating new job
                logger.info(f"[ExtractProblemInfoView] Extraction status is {extraction_status}, allowing new job creation")

            # Create a job record (only if problem is new or no existing job)
            job = ProblemExtractionJob.objects.create(
                platform=platform,
                problem_id=problem_id,
                problem_url=problem_url,
                problem_identifier=problem_id,  # Use problem_id as identifier
                status='PENDING'
            )
            logger.info(f"[ExtractProblemInfoView] Created job with ID: {job.id}")

            # Update problem metadata with job_id
            problem.metadata = {
                **(problem.metadata or {}),
                'extraction_job_id': job.id,
                'extraction_status': 'PENDING'
            }
            problem.save(update_fields=['metadata'])

            # Enqueue the job to Celery
            task = extract_problem_info_task.delay(problem_url, job.id)
            logger.info(f"[ExtractProblemInfoView] Enqueued task with ID: {task.id}")

            # Update job with task ID
            job.celery_task_id = task.id
            job.save(update_fields=['celery_task_id'])
            logger.info(f"[ExtractProblemInfoView] Job {job.id} updated with task ID: {task.id}")

            return Response({
                'problem_id': problem.id,
                'platform': problem.platform,
                'problem_identifier': problem.problem_id,
                'job_id': job.id,
                'status': job.status,
                'message': 'Problem draft created and extraction job queued for processing'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.exception(f"[ExtractProblemInfoView] Error: {str(e)}")
            return Response(
                {'error': f'Failed to create extraction job: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobProgressHistoryView(APIView):
    """Get progress history for a job"""
    permission_classes = [AllowAny]

    def get(self, request, job_id):
        """
        Get progress history for a specific job

        Query params:
            job_type: 'extraction' or 'generation' (default: 'extraction')

        Returns:
            {
                "job_id": 123,
                "history": [
                    {
                        "id": 1,
                        "step": "Fetching webpage...",
                        "message": "Fetching webpage...",
                        "status": "completed",
                        "created_at": "2025-10-07T12:00:00Z"
                    },
                    ...
                ]
            }
        """
        try:
            from ..models import JobProgressHistory
            from ..serializers import JobProgressHistorySerializer
            from django.contrib.contenttypes.models import ContentType

            # Determine job type
            job_type = request.query_params.get('job_type', 'extraction')

            if job_type == 'extraction':
                content_type = ContentType.objects.get_for_model(ProblemExtractionJob)
            elif job_type == 'generation':
                content_type = ContentType.objects.get_for_model(ScriptGenerationJob)
            else:
                return Response(
                    {'error': 'Invalid job_type. Must be "extraction" or "generation"'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get progress history
            history = JobProgressHistory.objects.filter(
                content_type=content_type,
                object_id=job_id
            ).order_by('created_at')

            serializer = JobProgressHistorySerializer(history, many=True)

            return Response({
                'job_id': job_id,
                'job_type': job_type,
                'history': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"[JobProgressHistoryView] Error: {str(e)}")
            return Response(
                {'error': f'Failed to fetch progress history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegenerateSolutionView(APIView):
    """Regenerate solution code for a draft problem with additional context"""
    permission_classes = [IsAuthenticated]

    def post(self, request, problem_id):
        """
        Regenerate solution code for a draft problem with additional context

        This endpoint triggers a new problem extraction job with additional context
        (e.g., counterexamples, edge cases) to generate an improved solution.

        Request body:
            {
                "additional_context": "The solution fails for case: n=1000000, expected output: ..."
            }

        Returns:
            {
                "job_id": 1,
                "status": "PENDING",
                "message": "Solution regeneration job created and queued"
            }
        """
        # Check if user is admin
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get the problem (optimized: only fetch needed fields)
            problem = Problem.objects.only(
                'id', 'platform', 'problem_id', 'title', 'problem_url',
                'tags', 'solution_code', 'language', 'constraints', 'is_completed'
            ).get(id=problem_id)

            # Verify it's a draft
            if problem.is_completed:
                return Response(
                    {'error': 'Cannot regenerate solution for completed problems. Only drafts can be regenerated.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get additional context
            additional_context = request.data.get('additional_context', '')

            # Validate problem URL exists
            if not problem.problem_url:
                return Response(
                    {'error': 'Problem URL is required for solution regeneration'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create a new extraction job with additional context
            job = ProblemExtractionJob.objects.create(
                platform=problem.platform,
                problem_id=problem.problem_id,
                problem_url=problem.problem_url,
                problem_identifier=problem.problem_id,
                status='PENDING'
            )

            # Update problem metadata with new job info and additional context
            problem.metadata = {
                **(problem.metadata or {}),
                'extraction_job_id': job.id,
                'extraction_status': 'PENDING',
                'additional_context': additional_context,
                'regeneration_attempt': True
            }
            problem.save(update_fields=['metadata'])

            # Enqueue the extraction task with additional context
            from ..tasks import extract_problem_info_task
            task = extract_problem_info_task.apply_async(
                kwargs={
                    'problem_url': problem.problem_url,
                    'job_id': job.id,
                    'additional_context': additional_context
                },
                queue='ai'
            )

            # Update job with task ID
            job.celery_task_id = task.id
            job.save(update_fields=['celery_task_id'])

            return Response({
                'job_id': job.id,
                'status': job.status,
                'message': 'Solution regeneration job created and queued for processing'
            }, status=status.HTTP_202_ACCEPTED)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"[RegenerateSolutionView] Error: {str(e)}")
            return Response(
                {'error': f'Failed to regenerate solution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
