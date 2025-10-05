"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from ..models import Problem, TestCase
from ..services.gemini_service import GeminiService
from ..services.code_executor import CodeExecutor
from ..services.test_case_generator import TestCaseGenerator
from ..serializers import (
    ProblemRegisterSerializer,
    GenerateTestCasesSerializer,
    ProblemSerializer,
    ProblemSaveSerializer
)


class GenerateTestCasesView(APIView):
    """Generate test case generator code using Gemini AI"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Generate Python code that will generate test cases using Gemini AI

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "language": "python",
                "constraints": "1 <= a, b <= 10"
            }

        Returns:
            {
                "generator_code": "def generate_test_cases():\n    ..."
            }
        """
        serializer = GenerateTestCasesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            gemini_service = GeminiService()
            generator_code = gemini_service.generate_test_case_generator_code(
                serializer.validated_data
            )

            # Validate the generated code
            TestCaseGenerator.validate_code(generator_code)

            return Response({
                'generator_code': generator_code
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate test case generator: {str(e)}'},
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

            # Step 1: Generate test case generator code using Gemini
            gemini_service = GeminiService()
            generator_code = gemini_service.generate_test_case_generator_code(
                serializer.validated_data
            )

            # Step 2: Execute the generator code locally to get test inputs
            # and then run solution to get outputs
            test_cases_with_outputs = TestCaseGenerator.generate_test_cases_with_outputs(
                generator_code=generator_code,
                solution_code=solution_code,
                language=language,
                code_executor=CodeExecutor
            )

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
