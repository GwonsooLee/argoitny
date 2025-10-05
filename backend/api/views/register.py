"""Problem Registration Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from ..models import Problem, TestCase
from ..services.gemini_service import GeminiService
from ..services.code_executor import CodeExecutor
from ..serializers import (
    ProblemRegisterSerializer,
    GenerateTestCasesSerializer,
    ProblemSerializer
)


class GenerateTestCasesView(APIView):
    """Generate test cases using Gemini AI"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Generate test cases using Gemini AI

        Request body:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "solution_code": "a, b = map(int, input().split())\\nprint(a + b)",
                "language": "python",
                "constraints": "1 <= a, b <= 10"
            }

        Returns:
            {
                "test_cases": [
                    {"input": "1 2"},
                    {"input": "5 5"},
                    ...
                ]
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
            test_cases = gemini_service.generate_test_cases(serializer.validated_data)

            return Response({
                'test_cases': test_cases
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate test cases: {str(e)}'},
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
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
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
        solution_code = serializer.validated_data['solution_code']
        language = serializer.validated_data['language']

        try:
            # Check if problem already exists
            if Problem.objects.filter(platform=platform, problem_id=problem_id).exists():
                return Response(
                    {'error': 'Problem already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate test cases using Gemini
            gemini_service = GeminiService()
            test_case_inputs = gemini_service.generate_test_cases(serializer.validated_data)

            # Execute solution code to get outputs
            test_cases_with_outputs = []
            for tc in test_case_inputs:
                execution_result = CodeExecutor.execute(
                    code=solution_code,
                    language=language,
                    input_data=tc['input']
                )

                if not execution_result['success']:
                    return Response(
                        {
                            'error': f'Solution code failed on input: {tc["input"]}',
                            'details': execution_result['error']
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                test_cases_with_outputs.append({
                    'input': tc['input'],
                    'output': execution_result['output'].strip()
                })

            # Save problem and test cases
            with transaction.atomic():
                problem = Problem.objects.create(
                    platform=platform,
                    problem_id=problem_id,
                    title=title
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
