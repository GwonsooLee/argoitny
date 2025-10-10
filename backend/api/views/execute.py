"""Code Execution Views - Async DynamoDB Implementation"""
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from ..authentication import CustomJWTAuthentication
from ..serializers import ExecuteCodeSerializer
from ..utils.rate_limit import check_rate_limit, log_usage
from ..dynamodb.async_client import AsyncDynamoDBClient
import logging

logger = logging.getLogger(__name__)


class ExecuteCodeView(APIView):
    """Execute code against test cases (async) - DynamoDB implementation"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def post(self, request):
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
        # Check rate limit (wrap sync function)
        allowed, current_count, limit, message = await sync_to_async(check_rate_limit)(
            request.user, 'execution'
        )
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
        # Validate serializer (sync operation, use sync_to_async for safety)
        is_valid = await sync_to_async(serializer.is_valid)()
        if not is_valid:
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
            # Determine platform and problem_identifier based on input
            if platform and problem_identifier:
                # New approach: Direct async DynamoDB lookup
                async with AsyncDynamoDBClient.get_resource() as resource:
                    table = await resource.Table(AsyncDynamoDBClient._table_name)

                    # Get problem metadata
                    problem_response = await table.get_item(
                        Key={
                            'PK': f'PROB#{platform}#{problem_identifier}',
                            'SK': 'META'
                        }
                    )

                    if 'Item' not in problem_response:
                        return Response(
                            {'error': f'Problem not found: {platform}/{problem_identifier}'},
                            status=status.HTTP_404_NOT_FOUND
                        )

                    problem_data = problem_response['Item']

                    # Get test cases using query
                    testcases_response = await table.query(
                        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                        ExpressionAttributeValues={
                            ':pk': f'PROB#{platform}#{problem_identifier}',
                            ':sk': 'TESTCASE#'
                        }
                    )

                    test_cases = testcases_response.get('Items', [])

                    # Check if problem has test cases
                    if not test_cases:
                        return Response(
                            {'error': 'No test cases found for this problem'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # DynamoDB only - no ORM problem reference needed

            elif problem_id:
                # Legacy approach: problem_id only (not supported in DynamoDB-only mode)
                return Response(
                    {
                        'error': 'Legacy problem_id is not supported. Please provide platform and problem_identifier.'
                    },
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

            # Get user ID (sync operation)
            user_id = await sync_to_async(lambda: request.user.id if request.user.is_authenticated else None)()

            # Delay celery task (sync operation)
            task = await sync_to_async(execute_code_task.delay)(
                code=code,
                language=language,
                platform=platform,
                problem_identifier=problem_identifier,
                user_id=user_id,
                user_identifier=user_identifier,
                is_code_public=is_code_public
            )

            # Log usage (wrap sync function)
            await sync_to_async(log_usage)(
                user=request.user,
                action='execution',
                problem=None,  # DynamoDB only - no ORM problem
                metadata={'task_id': task.id, 'language': language, 'platform': platform, 'problem_id': problem_identifier}
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
            logger.error(f'Failed to start code execution: {str(e)}', exc_info=True)
            return Response(
                {'error': f'Failed to start code execution: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
