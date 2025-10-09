"""Code Execution Views - DynamoDB Implementation"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..authentication import CustomJWTAuthentication
from django.db import transaction
from ..models import Problem, SearchHistory, TestCase
from ..services.code_executor import CodeExecutor
from ..serializers import ExecuteCodeSerializer
from ..utils.rate_limit import check_rate_limit, log_usage
from ..dynamodb.client import DynamoDBClient
from ..dynamodb.repositories import ProblemRepository


class ExecuteCodeView(APIView):
    """Execute code against test cases (async) - DynamoDB implementation"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Execute user code against problem test cases (async)

        Request body:
            {
                "code": "user code",
                "language": "python",
                "problem_id": 1,  # Legacy: Django ORM problem ID (optional)
                "platform": "baekjoon",  # New: DynamoDB platform (optional)
                "problem_identifier": "1000",  # New: DynamoDB problem_id (optional)
                "user_identifier": "user@example.com",  # optional
                "is_code_public": false  # optional
            }

        Note: Either provide problem_id (legacy) OR platform+problem_identifier (new)

        Returns:
            {
                "message": "Code execution task started",
                "task_id": "abc123..."
            }
        """
        # Check rate limit
        allowed, current_count, limit, message = check_rate_limit(request.user, 'execution')
        if not allowed:
            return Response(
                {
                    'error': message,
                    'current_count': current_count,
                    'limit': limit
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = ExecuteCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        code = serializer.validated_data['code']
        language = serializer.validated_data['language']
        user_identifier = serializer.validated_data.get('user_identifier', 'anonymous')
        is_code_public = serializer.validated_data.get('is_code_public', False)

        # Extract problem identification - support both legacy and new approaches
        problem_id = serializer.validated_data.get('problem_id')
        platform = request.data.get('platform')
        problem_identifier = request.data.get('problem_identifier')

        try:
            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            problem_repo = ProblemRepository(table)

            # Determine platform and problem_identifier based on input
            if platform and problem_identifier:
                # New approach: Direct DynamoDB lookup
                problem_data = problem_repo.get_problem_with_testcases(
                    platform=platform,
                    problem_id=problem_identifier
                )

                if not problem_data:
                    return Response(
                        {'error': f'Problem not found: {platform}/{problem_identifier}'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Check if problem has test cases
                test_cases = problem_data.get('test_cases', [])
                if not test_cases:
                    return Response(
                        {'error': 'No test cases found for this problem'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # For backward compatibility with log_usage, try to get Django ORM Problem
                # This is optional - if it doesn't exist, we'll pass None
                orm_problem = None
                try:
                    orm_problem = Problem.objects.only('id').get(
                        platform=platform,
                        problem_id=problem_identifier
                    )
                except Problem.DoesNotExist:
                    # This is fine - we're transitioning to DynamoDB
                    pass

            elif problem_id:
                # Legacy approach: Django ORM problem_id lookup
                # First get the Problem to extract platform/problem_identifier
                try:
                    orm_problem = Problem.objects.only(
                        'id', 'platform', 'problem_id'
                    ).get(id=problem_id)
                except Problem.DoesNotExist:
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                platform = orm_problem.platform
                problem_identifier = orm_problem.problem_id

                # Now verify test cases exist in DynamoDB
                problem_data = problem_repo.get_problem_with_testcases(
                    platform=platform,
                    problem_id=problem_identifier
                )

                if not problem_data:
                    # Fallback to Django ORM for backward compatibility
                    if not TestCase.objects.filter(problem=orm_problem).exists():
                        return Response(
                            {'error': 'No test cases found for this problem'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    # Check DynamoDB test cases
                    test_cases = problem_data.get('test_cases', [])
                    if not test_cases:
                        return Response(
                            {'error': 'No test cases found for this problem'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                return Response(
                    {
                        'error': 'Either problem_id OR (platform + problem_identifier) must be provided'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Start async task with platform and problem_identifier
            from api.tasks import execute_code_task
            user_id = request.user.id if request.user.is_authenticated else None
            task = execute_code_task.delay(
                code=code,
                language=language,
                platform=platform,
                problem_identifier=problem_identifier,
                user_id=user_id,
                user_identifier=user_identifier,
                is_code_public=is_code_public
            )

            # Log usage - pass ORM problem if available for backward compatibility
            log_usage(
                user=request.user,
                action='execution',
                problem=orm_problem if 'orm_problem' in locals() else None,
                metadata={'task_id': task.id, 'language': language}
            )

            return Response({
                'message': 'Code execution task started',
                'task_id': task.id,
                'usage': {
                    'current_count': current_count + 1,
                    'limit': limit
                }
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Failed to start code execution: {str(e)}', exc_info=True)
            return Response(
                {'error': f'Failed to start code execution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
