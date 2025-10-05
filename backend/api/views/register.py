"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
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

            # Update job with task ID
            job.celery_task_id = task.id
            job.save()

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
            # Check if problem already exists
            if Problem.objects.filter(platform=platform, problem_id=problem_id).exists():
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

            # Check if problem already exists
            existing_problem = Problem.objects.filter(
                platform=platform,
                problem_id=problem_id
            ).first()

            if existing_problem:
                # Update existing problem
                for key, value in serializer.validated_data.items():
                    setattr(existing_problem, key, value)
                existing_problem.save()
                problem = existing_problem
            else:
                # Create new problem
                problem = Problem.objects.create(**serializer.validated_data)

        # Serialize response
        response_serializer = ProblemSaveSerializer(problem)

        return Response({
            'message': 'Problem saved successfully',
            'problem': response_serializer.data
        }, status=status.HTTP_200_OK)
