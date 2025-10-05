"""Code Execution Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from ..models import Problem, SearchHistory
from ..services.code_executor import CodeExecutor
from ..serializers import ExecuteCodeSerializer


class ExecuteCodeView(APIView):
    """Execute code against test cases"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Execute user code against problem test cases

        Request body:
            {
                "code": "user code",
                "language": "python",
                "problem_id": 1,
                "user_identifier": "user@example.com",  # optional
                "is_code_public": false  # optional
            }

        Returns:
            {
                "results": [
                    {
                        "test_case_id": 1,
                        "input": "1 2",
                        "expected": "3",
                        "output": "3",
                        "passed": true,
                        "error": null
                    },
                    ...
                ],
                "summary": {
                    "total": 100,
                    "passed": 95,
                    "failed": 5
                }
            }
        """
        serializer = ExecuteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        code = serializer.validated_data['code']
        language = serializer.validated_data['language']
        problem_id = serializer.validated_data['problem_id']
        user_identifier = serializer.validated_data.get('user_identifier', 'anonymous')
        is_code_public = serializer.validated_data.get('is_code_public', False)

        try:
            # Get problem with test cases
            problem = Problem.objects.prefetch_related('test_cases').get(id=problem_id)

            if not problem.test_cases.exists():
                return Response(
                    {'error': 'No test cases found for this problem'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Execute code against each test case
            results = []
            passed_count = 0
            failed_count = 0

            for test_case in problem.test_cases.all():
                execution_result = CodeExecutor.execute(
                    code=code,
                    language=language,
                    input_data=test_case.input
                )

                # Compare output (strip whitespace for comparison)
                output = execution_result['output'].strip()
                expected = test_case.output.strip()
                passed = execution_result['success'] and output == expected

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1

                results.append({
                    'test_case_id': test_case.id,
                    'input': test_case.input,
                    'expected': expected,
                    'output': output,
                    'passed': passed,
                    'error': execution_result['error'] if not execution_result['success'] else None
                })

            # Save to search history
            user = request.user if request.user.is_authenticated else None

            with transaction.atomic():
                search_history = SearchHistory.objects.create(
                    user=user,
                    user_identifier=user_identifier,
                    problem=problem,
                    platform=problem.platform,
                    problem_number=problem.problem_id,
                    problem_title=problem.title,
                    language=language,
                    code=code,
                    result_summary='passed' if failed_count == 0 else 'failed',
                    passed_count=passed_count,
                    failed_count=failed_count,
                    total_count=passed_count + failed_count,
                    is_code_public=is_code_public
                )

            return Response({
                'results': results,
                'summary': {
                    'total': passed_count + failed_count,
                    'passed': passed_count,
                    'failed': failed_count
                },
                'history_id': search_history.id
            }, status=status.HTTP_200_OK)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Code execution failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
