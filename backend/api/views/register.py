"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from ..models import Problem, TestCase, ScriptGenerationJob
from ..services.gemini_service import GeminiService
from ..services.code_executor import CodeExecutor
from ..services.test_case_generator import TestCaseGenerator
from ..services.code_execution_service import CodeExecutionService
from ..serializers import (
    ProblemRegisterSerializer,
    GenerateTestCasesSerializer,
    ProblemSerializer,
    ProblemSaveSerializer,
    ScriptGenerationJobSerializer
)
from ..tasks import generate_script_task


class GenerateTestCasesView(APIView):
    """Generate test case generator code using Gemini AI"""
    permission_classes = [AllowAny]

    def post(self, request):
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
                problem_url=request.data.get('problem_url', ''),
                tags=request.data.get('tags', []),
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
    permission_classes = [AllowAny]

    def post(self, request):
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
        Get all draft problems (problems without test cases)

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
            # Get problems that have no test cases (drafts)
            from django.db.models import Count
            import base64

            drafts = Problem.objects.annotate(
                test_case_count=Count('test_cases')
            ).filter(test_case_count=0).order_by('-created_at')

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
                })

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
            jobs = ScriptGenerationJob.objects.all()

            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                jobs = jobs.filter(status=status_filter.upper())

            # Filter by platform if provided
            platform = request.query_params.get('platform')
            if platform:
                jobs = jobs.filter(platform=platform)

            # Filter by problem_id if provided
            problem_id = request.query_params.get('problem_id')
            if problem_id:
                jobs = jobs.filter(problem_id=problem_id)

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
        Get details of a specific job with generated test cases

        Returns:
            {
                "id": 1,
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "status": "COMPLETED",
                "generator_code": "...",
                "test_cases": ["1 2", "3 4", ...],
                "error_message": null,
                "created_at": "...",
                "updated_at": "..."
            }
        """
        try:
            job = ScriptGenerationJob.objects.get(id=job_id)
            serializer = ScriptGenerationJobSerializer(job)
            response_data = serializer.data

            # If job is completed and has generator code, execute it to get test cases
            if job.status == 'COMPLETED' and job.generator_code:
                try:
                    test_cases = TestCaseGenerator.execute_generator_code(
                        code=job.generator_code,
                        num_cases=20
                    )
                    response_data['test_cases'] = test_cases
                except Exception as e:
                    response_data['test_cases'] = []
                    response_data['test_case_error'] = str(e)
            else:
                response_data['test_cases'] = []

            return Response(response_data, status=status.HTTP_200_OK)

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

        try:
            problem = Problem.objects.only('id', 'is_completed').get(platform=platform, problem_id=problem_id)
            problem.is_completed = is_completed
            problem.save(update_fields=['is_completed'])

            message = 'Problem marked as completed' if is_completed else 'Problem marked as draft'
            return Response({
                'message': message,
                'is_completed': problem.is_completed
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
            serializer = ProblemSaveSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            platform = serializer.validated_data['platform']
            problem_id = serializer.validated_data['problem_id']

            # Use update_or_create for atomic operation (optimized)
            problem, created = Problem.objects.update_or_create(
                platform=platform,
                problem_id=problem_id,
                defaults=serializer.validated_data
            )

        # Serialize response
        response_serializer = ProblemSaveSerializer(problem)

        return Response({
            'message': 'Problem saved successfully',
            'problem': response_serializer.data
        }, status=status.HTTP_200_OK)
