"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from ..services.gemini_service import GeminiService
from ..serializers import (
    ProblemRegisterSerializer,
    ProblemSerializer,
    ProblemSaveSerializer,
    ScriptGenerationJobSerializer,
    ExtractProblemInfoSerializer
)
from ..tasks import generate_script_task, extract_problem_info_task
from ..dynamodb.client import DynamoDBClient
from ..dynamodb.repositories import ProblemRepository, ProblemExtractionJobRepository, ScriptGenerationJobRepository
from ..utils.job_helper import JobHelper
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
            # Create a job record using JobHelper
            job = JobHelper.create_script_generation_job(
                platform=serializer.validated_data['platform'],
                problem_id=serializer.validated_data['problem_id'],
                title=serializer.validated_data['title'],
                problem_url=serializer.validated_data.get('problem_url', ''),
                tags=serializer.validated_data.get('tags', []),
                language=serializer.validated_data['language'],
                constraints=serializer.validated_data['constraints'],
                status='PENDING'
            )

            # Enqueue the job to Celery
            task = generate_script_task.delay(job['id'])

            # Update job with task ID
            JobHelper.update_script_generation_job(job['id'], {'celery_task_id': task.id})

            return Response({
                'job_id': job['id'],
                'status': job['status'],
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
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "problem_url": "https://www.acmicpc.net/problem/1000",
                    "tags": ["math", "implementation"],
                    "created_at": "...",
                    "test_cases": [
                        {
                            "testcase_id": "1",
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
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Check if problem already exists
            existing_problem = problem_repo.get_problem(platform, problem_id)
            if existing_problem:
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

            # Create problem in DynamoDB
            problem_data = {
                'title': title,
                'problem_url': problem_url or '',
                'tags': tags,
                'solution_code': solution_code,
                'language': language,
                'is_completed': True  # Mark as completed since we're registering with test cases
            }

            problem_item = problem_repo.create_problem(
                platform=platform,
                problem_id=problem_id,
                problem_data=problem_data
            )

            # Add test cases (with numbering: 1, 2, 3...)
            for idx, tc in enumerate(test_cases_with_outputs, start=1):
                problem_repo.add_testcase(
                    platform=platform,
                    problem_id=problem_id,
                    testcase_id=str(idx),
                    input_str=tc['input'],
                    output_str=tc['output']
                )

            # Fetch problem with test cases for response
            problem = problem_repo.get_problem_with_testcases(platform, problem_id)

            return Response({
                'message': 'Problem registered successfully',
                'problem': problem
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Failed to register problem: {str(e)}")
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
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Get draft problems from DynamoDB
            drafts = problem_repo.list_draft_problems(limit=100)

            # Process drafts to decode solution_code from base64
            import base64
            draft_data = []
            for problem in drafts:
                # Decode solution_code from base64
                solution_code = problem.get('solution_code', '')
                if solution_code:
                    try:
                        solution_code = base64.b64decode(solution_code).decode('utf-8')
                    except:
                        # If decoding fails, use as-is
                        pass

                # Get extraction job status if available
                metadata = problem.get('metadata', {})
                extraction_status = metadata.get('extraction_status')
                extraction_job_id = metadata.get('extraction_job_id')

                draft_data.append({
                    'id': f"{problem['platform']}#{problem['problem_id']}",  # Use composite key as ID
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': problem.get('title', ''),
                    'problem_url': problem.get('problem_url', ''),
                    'tags': problem.get('tags', []),
                    'solution_code': solution_code,
                    'language': problem.get('language', 'python'),
                    'constraints': problem.get('constraints', ''),
                    'created_at': problem.get('created_at', ''),
                    'extraction_status': extraction_status,
                    'extraction_job_id': extraction_job_id,
                })

            # Also include extraction jobs that haven't created Problems yet
            # Get both PENDING and PROCESSING jobs
            pending_jobs = []
            for job_status in ['PENDING', 'PROCESSING']:
                jobs, _ = JobHelper.list_problem_extraction_jobs(status=job_status)
                pending_jobs.extend(jobs)

            # Get job IDs that are already in draft_data
            existing_job_ids = {d.get('extraction_job_id') for d in draft_data if d.get('extraction_job_id')}

            # Add jobs that don't have corresponding Problems yet
            for job in pending_jobs:
                job_id = job.get('id')
                if job_id not in existing_job_ids:
                    # Format job for display
                    formatted_job = JobHelper.format_job_for_serializer(job)
                    draft_data.append({
                        'id': None,  # No Problem ID yet
                        'platform': job.get('platform') or 'unknown',
                        'problem_id': job.get('problem_id') or 'extracting',
                        'title': job.get('title') or 'Extracting problem info...',
                        'problem_url': job.get('problem_url') or '',
                        'tags': [],
                        'solution_code': '',
                        'language': 'cpp',
                        'constraints': '',
                        'created_at': formatted_job.get('created_at', ''),
                        'extraction_status': job.get('status'),
                        'extraction_job_id': job_id,
                        'is_extracting': True,  # Flag to indicate this is still being extracted
                    })

            # Re-sort by created_at after adding pending jobs
            draft_data.sort(key=lambda x: x['created_at'], reverse=True)

            return Response({
                'drafts': draft_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to fetch drafts: {str(e)}")
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
            # Get filter parameters
            status_filter = request.query_params.get('status')
            platform = request.query_params.get('platform')
            problem_id = request.query_params.get('problem_id')

            # List jobs using JobHelper
            jobs, _ = JobHelper.list_script_generation_jobs(
                status=status_filter.upper() if status_filter else None,
                platform=platform,
                problem_id=problem_id
            )

            # Format jobs for serializer (convert timestamps)
            formatted_jobs = [JobHelper.format_job_for_serializer(job) for job in jobs]

            # Exclude generator_code field from list view for optimization
            for job in formatted_jobs:
                job.pop('generator_code', None)

            return Response({
                'jobs': formatted_jobs
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
            job = JobHelper.get_script_generation_job(job_id)
            if not job:
                return Response(
                    {'error': 'Job not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            formatted_job = JobHelper.format_job_for_serializer(job)
            return Response(formatted_job, status=status.HTTP_200_OK)

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
            # Check if job exists
            job = JobHelper.get_script_generation_job(job_id)
            if not job:
                return Response(
                    {'error': 'Job not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Delete the job
            JobHelper.delete_script_generation_job(job_id)

            return Response({
                'message': 'Job deleted successfully'
            }, status=status.HTTP_200_OK)

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
            job = JobHelper.get_problem_extraction_job(job_id)
            if not job:
                return Response(
                    {'error': 'Job not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if job is in a retry-able state
            # Allow FAILED, PROCESSING (cancel & retry), COMPLETED (re-extract), PENDING (restart)
            job_status = job.get('status')
            if job_status not in ['FAILED', 'PROCESSING', 'COMPLETED', 'PENDING']:
                return Response(
                    {'error': f'Job status is {job_status}. Cannot retry this job.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the problem URL and other info from old job
            problem_url = job.get('problem_url')
            if not problem_url:
                return Response(
                    {'error': 'Job does not have a problem_url to retry'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            platform = job.get('platform')
            problem_id = job.get('problem_id')
            problem_identifier = job.get('problem_identifier')
            title = job.get('title', '')

            # Cancel the old job (mark as CANCELLED to prevent race conditions)
            JobHelper.update_problem_extraction_job(job_id, {
                'status': 'CANCELLED',
                'error_message': 'Cancelled for retry'
            })
            logger.info(f"Cancelled old job {job_id}")

            # Create a NEW job for the retry
            new_job = JobHelper.create_problem_extraction_job(
                platform=platform,
                problem_id=problem_id,
                problem_url=problem_url,
                problem_identifier=problem_identifier,
                title=title,
                status='PENDING'
            )
            new_job_id = new_job['id']
            logger.info(f"Created new retry job {new_job_id}")

            # Update Problem metadata to reflect retry in DynamoDB
            try:
                from ..dynamodb.client import DynamoDBClient
                from ..dynamodb.repositories import ProblemRepository

                table = DynamoDBClient.get_table()
                problem_repo = ProblemRepository(table)
                problem = problem_repo.get_problem(platform, problem_id)

                if problem:
                    metadata = problem.get('metadata', {})
                    metadata.update({
                        'extraction_status': 'PENDING',
                        'extraction_job_id': new_job_id,
                        'progress': 'Retry initiated...',
                        'error_message': None
                    })
                    problem_repo.update_problem(
                        platform=platform,
                        problem_id=problem_id,
                        updates={'metadata': metadata}
                    )
                    logger.info(f"Updated Problem {platform}/{problem_id} to PENDING with new job {new_job_id}")
                else:
                    logger.warning(f"Problem {platform}/{problem_id} not found in DynamoDB")
            except Exception as e:
                logger.warning(f"Failed to update problem metadata: {str(e)}")

            # Trigger the extraction task with NEW job_id
            from ..tasks import extract_problem_info_task
            extract_problem_info_task.apply_async(
                kwargs={
                    'problem_url': problem_url,
                    'job_id': new_job_id
                },
                queue='ai'
            )

            return Response({
                'message': 'Extraction job retry initiated',
                'old_job_id': job_id,
                'job_id': new_job_id,
                'status': 'PENDING'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to retry job: {str(e)}")
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
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Check if problem exists
            problem = problem_repo.get_problem(platform, problem_id)
            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Delete existing test cases (by deleting and recreating problem with test cases)
            # First, get the problem metadata
            existing_testcases = problem_repo.get_testcases(platform, problem_id)

            # Delete each test case
            for tc in existing_testcases:
                # Use delete_item from base repository
                pk = f'PROB#{platform}#{problem_id}'
                sk = f"TC#{tc['testcase_id']}"
                problem_repo.delete_item(pk, sk)

            # Create new test cases with empty outputs (numbered 1, 2, 3...)
            for idx, inp in enumerate(test_inputs, start=1):
                problem_repo.add_testcase(
                    platform=platform,
                    problem_id=problem_id,
                    testcase_id=str(idx),
                    input_str=inp,
                    output_str=''  # Empty output for now
                )

            return Response({
                'message': 'Test cases saved successfully',
                'count': len(test_inputs)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to save test cases: {str(e)}")
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
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Verify problem exists and has solution code
            problem = problem_repo.get_problem_with_testcases(platform, problem_id)

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not problem.get('solution_code'):
                return Response(
                    {'error': 'Problem has no solution code'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            test_cases = problem.get('test_cases', [])
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

        except Exception as e:
            logger.exception(f"Failed to start output generation: {str(e)}")
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
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Check if problem exists
            problem = problem_repo.get_problem(platform, problem_id)
            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update completion status
            problem_repo.update_problem(
                platform=platform,
                problem_id=problem_id,
                updates={'is_completed': is_completed}
            )

            message = 'Problem marked as completed' if is_completed else 'Problem marked as draft'
            return Response({
                'message': message,
                'is_completed': is_completed
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to update completion status: {str(e)}")
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
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "problem_url": "https://www.acmicpc.net/problem/1000",
                    "tags": ["math", "implementation"]
                }
            }
        """
        # Check for ID (composite key format: platform#problem_id)
        draft_id = request.data.get('id')

        platform = request.data.get('platform')
        problem_id = request.data.get('problem_id')

        # Parse ID if provided
        if draft_id and '#' in str(draft_id):
            parts = str(draft_id).split('#', 1)
            platform = parts[0]
            problem_id = parts[1] if len(parts) > 1 else problem_id

        if not platform or not problem_id:
            return Response(
                {'error': 'platform and problem_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Check if problem already exists
            existing_problem = problem_repo.get_problem(platform, problem_id)

            # Prepare problem data
            problem_data = {
                'title': request.data.get('title', ''),
                'problem_url': request.data.get('problem_url', ''),
                'tags': request.data.get('tags', []),
                'solution_code': request.data.get('solution_code', ''),
                'language': request.data.get('language', 'python'),
                'constraints': request.data.get('constraints', ''),
                'is_completed': request.data.get('is_completed', False),
                'metadata': request.data.get('metadata', {})
            }

            if existing_problem:
                # Update existing problem
                updates = {}
                for key in ['title', 'problem_url', 'tags', 'solution_code', 'language',
                           'constraints', 'is_completed', 'metadata']:
                    if key in problem_data:
                        updates[key] = problem_data[key]

                problem_repo.update_problem(
                    platform=platform,
                    problem_id=problem_id,
                    updates=updates
                )
                problem = problem_repo.get_problem(platform, problem_id)
            else:
                # Create new problem
                problem_repo.create_problem(
                    platform=platform,
                    problem_id=problem_id,
                    problem_data=problem_data
                )
                problem = problem_repo.get_problem(platform, problem_id)

            return Response({
                'message': 'Problem saved successfully',
                'problem': problem
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Failed to save problem: {str(e)}")
            return Response(
                {'error': f'Failed to save problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                "problem_id": "baekjoon#1000",
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

            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Check if problem already exists in DynamoDB
            existing_problem = problem_repo.get_problem(platform, problem_id)

            created = False
            if not existing_problem:
                # Create Problem immediately as draft in DynamoDB
                problem_data = {
                    'title': f'{platform.upper()} {problem_id}',
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
                problem_repo.create_problem(
                    platform=platform,
                    problem_id=problem_id,
                    problem_data=problem_data
                )
                created = True
                logger.info(f"[ExtractProblemInfoView] Created Problem: {platform}/{problem_id}")
            else:
                logger.info(f"[ExtractProblemInfoView] Found existing Problem: {platform}/{problem_id}")

            # If problem already exists, check if we should create a new job
            if not created:
                # Get extraction status
                metadata = existing_problem.get('metadata', {})
                extraction_status = metadata.get('extraction_status')
                constraints = existing_problem.get('constraints', '')
                is_completed = existing_problem.get('is_completed', False)

                # If extraction is completed or problem is marked as completed, don't create new job
                if extraction_status == 'COMPLETED' or is_completed or constraints:
                    logger.info(f"[ExtractProblemInfoView] Problem already fully extracted. extraction_status={extraction_status}, is_completed={is_completed}")
                    return Response({
                        'problem_id': f"{platform}#{problem_id}",
                        'platform': platform,
                        'problem_identifier': problem_id,
                        'job_id': None,
                        'status': 'COMPLETED',
                        'message': 'This problem has already been registered and extraction is complete. View your problem below.',
                        'already_exists': True
                    }, status=status.HTTP_200_OK)

                # If extraction is in progress or pending, return existing job info
                if extraction_status in ['PROCESSING', 'PENDING']:
                    existing_job_id = metadata.get('extraction_job_id')
                    if existing_job_id:
                        existing_job = JobHelper.get_problem_extraction_job(existing_job_id)
                        if existing_job:
                            logger.info(f"[ExtractProblemInfoView] Found existing job {existing_job['id']} with status {existing_job['status']}")

                            # Return existing draft info without creating new job
                            return Response({
                                'problem_id': f"{platform}#{problem_id}",
                                'platform': platform,
                                'problem_identifier': problem_id,
                                'job_id': existing_job['id'],
                                'status': existing_job['status'],
                                'message': f'Problem extraction is already in progress. Current status: {existing_job["status"]}. View your draft below.',
                                'already_exists': True
                            }, status=status.HTTP_200_OK)
                        else:
                            logger.info(f"[ExtractProblemInfoView] Job {existing_job_id} not found, creating new job")
                            pass  # Job was deleted, create a new one

                # If extraction failed, allow retry by creating new job
                logger.info(f"[ExtractProblemInfoView] Extraction status is {extraction_status}, allowing new job creation")

            # Create a job record (only if problem is new or no existing job)
            job = JobHelper.create_problem_extraction_job(
                platform=platform,
                problem_id=problem_id,
                problem_url=problem_url,
                problem_identifier=problem_id,  # Use problem_id as identifier
                status='PENDING'
            )
            logger.info(f"[ExtractProblemInfoView] Created job with ID: {job['id']}")

            # Update problem metadata with job_id in DynamoDB
            metadata = existing_problem.get('metadata', {}) if existing_problem else {}
            metadata.update({
                'extraction_job_id': job['id'],
                'extraction_status': 'PENDING'
            })
            problem_repo.update_problem(
                platform=platform,
                problem_id=problem_id,
                updates={'metadata': metadata}
            )

            # Enqueue the job to Celery
            task = extract_problem_info_task.delay(problem_url, job['id'])
            logger.info(f"[ExtractProblemInfoView] Enqueued task with ID: {task.id}")

            # Update job with task ID
            JobHelper.update_problem_extraction_job(job['id'], {'celery_task_id': task.id})
            logger.info(f"[ExtractProblemInfoView] Job {job['id']} updated with task ID: {task.id}")

            return Response({
                'problem_id': f"{platform}#{problem_id}",
                'platform': platform,
                'problem_identifier': problem_id,
                'job_id': job['id'],
                'status': job['status'],
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
        Get progress history for a specific job from DynamoDB with pagination

        Query params:
            job_type: 'extraction' or 'generation' (default: 'extraction')
            cursor: Pagination cursor (base64-encoded JSON from previous response)
            limit: Number of items per page (default: 100, max: 100)

        Returns:
            {
                "job_id": 123,
                "history": [
                    {
                        "id": "PROG#1696752000",
                        "step": "Fetching webpage...",
                        "message": "Fetching webpage...",
                        "status": "completed",
                        "created_at": "2025-10-07T12:00:00Z"
                    },
                    ...
                ],
                "next_cursor": "base64-encoded-cursor" or null
            }
        """
        try:
            from ..dynamodb.repositories import JobProgressHistoryRepository
            from datetime import datetime, timezone
            import json
            import base64

            # Determine job type
            job_type = request.query_params.get('job_type', 'extraction')

            if job_type not in ['extraction', 'generation']:
                return Response(
                    {'error': 'Invalid job_type. Must be "extraction" or "generation"'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get pagination parameters
            cursor = request.query_params.get('cursor')
            limit = min(int(request.query_params.get('limit', 100)), 100)

            # Decode cursor if provided
            last_evaluated_key = None
            if cursor:
                try:
                    last_evaluated_key = json.loads(base64.b64decode(cursor).decode('utf-8'))
                except Exception:
                    return Response(
                        {'error': 'Invalid cursor format'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            progress_repo = JobProgressHistoryRepository(table)

            # Get progress history from DynamoDB with pagination
            history_items, next_key = progress_repo.get_progress_history(
                job_type=job_type,
                job_id=job_id,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )

            # Transform to response format with ISO timestamps
            history_data = []
            for item in history_items:
                # Convert Unix timestamp to ISO format
                created_timestamp = int(item.get('created_at', 0))
                created_at_iso = datetime.fromtimestamp(created_timestamp, tz=timezone.utc).isoformat() if created_timestamp else None

                history_data.append({
                    'id': item['id'],
                    'step': item['step'],
                    'message': item['message'],
                    'status': item['status'],
                    'created_at': created_at_iso
                })

            # Encode next cursor if available
            next_cursor = None
            if next_key:
                # Convert Decimal to int/float for JSON serialization
                from decimal import Decimal
                def convert_decimals(obj):
                    if isinstance(obj, dict):
                        return {k: convert_decimals(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(item) for item in obj]
                    elif isinstance(obj, Decimal):
                        return int(obj) if obj % 1 == 0 else float(obj)
                    return obj

                next_key = convert_decimals(next_key)
                next_cursor = base64.b64encode(json.dumps(next_key).encode('utf-8')).decode('utf-8')

            return Response({
                'job_id': job_id,
                'job_type': job_type,
                'history': history_data,
                'next_cursor': next_cursor
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
            # Parse problem_id (format: platform#problem_id)
            if '#' not in str(problem_id):
                return Response(
                    {'error': 'Invalid problem_id format. Expected: platform#problem_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            parts = str(problem_id).split('#', 1)
            platform = parts[0]
            prob_id = parts[1]

            # Initialize DynamoDB repository
            problem_repo = ProblemRepository()

            # Get the problem
            problem = problem_repo.get_problem(platform, prob_id)

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Verify it's a draft
            if problem.get('is_completed', False):
                return Response(
                    {'error': 'Cannot regenerate solution for completed problems. Only drafts can be regenerated.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get additional context
            additional_context = request.data.get('additional_context', '')

            # Validate problem URL exists
            problem_url = problem.get('problem_url', '')
            if not problem_url:
                return Response(
                    {'error': 'Problem URL is required for solution regeneration'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create a new extraction job with additional context
            job = JobHelper.create_problem_extraction_job(
                platform=platform,
                problem_id=prob_id,
                problem_url=problem_url,
                problem_identifier=prob_id,
                status='PENDING'
            )

            # Update problem metadata with new job info and additional context
            metadata = problem.get('metadata', {})
            metadata.update({
                'extraction_job_id': job['id'],
                'extraction_status': 'PENDING',
                'additional_context': additional_context,
                'regeneration_attempt': True
            })
            problem_repo.update_problem(
                platform=platform,
                problem_id=prob_id,
                updates={'metadata': metadata}
            )

            # Enqueue the extraction task with additional context
            from ..tasks import extract_problem_info_task
            task = extract_problem_info_task.apply_async(
                kwargs={
                    'problem_url': problem_url,
                    'job_id': job['id'],
                    'additional_context': additional_context
                },
                queue='ai'
            )

            # Update job with task ID
            JobHelper.update_problem_extraction_job(job['id'], {'celery_task_id': task.id})

            return Response({
                'job_id': job['id'],
                'status': job['status'],
                'message': 'Solution regeneration job created and queued for processing'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.exception(f"[RegenerateSolutionView] Error: {str(e)}")
            return Response(
                {'error': f'Failed to regenerate solution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
