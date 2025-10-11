"""Problem Hints Generation View"""
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from django.conf import settings
from ..dynamodb.async_client import AsyncDynamoDBClient
from ..tasks import generate_problem_hints_task
from ..utils.rate_limit import log_usage
import logging

logger = logging.getLogger(__name__)


class GenerateProblemHintsView(APIView):
    """Generate hints for a problem based on its solution"""
    permission_classes = [IsAuthenticated]

    async def post(self, request, platform=None, problem_id=None):
        """
        Start async hint generation task for the problem

        Request body: {} (empty, all data comes from problem)

        Returns:
            {
                "message": "Hint generation started",
                "task_id": "celery-task-id-123"
            }
        """
        # Check if user is admin
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
        except (AttributeError, Exception):
            is_admin = False

        if not is_admin:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Validate parameters
            if not platform or not problem_id:
                return Response(
                    {'error': 'Please provide both platform and problem_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get problem from DynamoDB to validate it exists
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_id}',
                        'SK': 'META'
                    }
                )

                if 'Item' not in problem_response:
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                problem = problem_response['Item']
                dat = problem.get('dat', {})

                # Check if problem has solution and is not under review
                if not dat.get('sol'):
                    return Response(
                        {'error': 'Problem must have a solution to generate hints'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if dat.get('nrv', False):
                    return Response(
                        {'error': 'Cannot generate hints for problems under review'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check if hints already exist
                metadata = dat.get('met', {})
                if metadata.get('hints'):
                    return Response(
                        {
                            'message': 'Hints already exist',
                            'hints': metadata['hints']
                        },
                        status=status.HTTP_200_OK
                    )

            # Start async task
            task = await sync_to_async(generate_problem_hints_task.delay)(platform, problem_id)

            logger.info(f"Started hint generation task {task.id} for problem {platform}/{problem_id}")

            return Response(
                {
                    'message': 'Hint generation started',
                    'task_id': task.id
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"Error starting hint generation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'Failed to start hint generation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetProblemHintsView(APIView):
    """Get hints for a problem (with plan-based rate limiting)"""
    permission_classes = [IsAuthenticated]

    async def get(self, request, platform=None, problem_id=None):
        """
        Get hints for a specific problem with plan-based rate limiting

        This endpoint checks the user's plan limits BEFORE returning hints,
        and logs the usage after successful retrieval.

        Args:
            platform: Problem platform (e.g., 'baekjoon', 'codeforces')
            problem_id: Problem identifier

        Returns:
            {
                "hints": [
                    {"level": 1, "hint": "..."},
                    {"level": 2, "hint": "..."}
                ]
            }
            or
            {
                "hints": []
            }
            or (429 - rate limit exceeded)
            {
                "error": "Hint limit exceeded",
                "message": "Daily hint limit exceeded (5/5). Resets at ...",
                "current_count": 5,
                "limit": 5
            }
        """
        try:
            # Validate parameters
            if not platform or not problem_id:
                return Response(
                    {'error': 'Please provide both platform and problem_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check plan-based rate limit BEFORE returning hints
            from ..utils.rate_limit import check_rate_limit, log_usage
            allowed, current_count, limit, message = await sync_to_async(check_rate_limit)(
                request.user,
                'hint'
            )

            if not allowed:
                return Response(
                    {
                        'error': 'Hint limit exceeded',
                        'message': message,
                        'current_count': current_count,
                        'limit': limit
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # Get problem hints from DynamoDB
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_id}',
                        'SK': 'META'
                    }
                )

                if 'Item' not in problem_response:
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                problem = problem_response['Item']
                dat = problem.get('dat', {})

                # Check if problem is completed
                if not dat.get('cmp', False):
                    return Response(
                        {'error': 'Problem not available'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Get hints from metadata
                metadata = dat.get('met', {})
                hints = metadata.get('hints', [])

                # Only log usage if hints exist and were successfully retrieved
                if hints:
                    await sync_to_async(log_usage)(
                        user=request.user,
                        action='hint',
                        problem={'platform': platform, 'number': problem_id},
                        metadata={'hint_type': 'problem_hints'}
                    )
                    logger.info(f"User {request.user.email} viewed hints for {platform}/{problem_id}")

                return Response(
                    {'hints': hints},
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            logger.error(f"Error fetching problem hints: {e}")
            return Response(
                {'error': f'Failed to fetch hints: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
