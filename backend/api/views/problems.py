"""Problem Views with DynamoDB Backend - True Async Version"""
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async
from datetime import datetime
from decimal import Decimal
from ..dynamodb.async_client import AsyncDynamoDBClient
import logging
import time

logger = logging.getLogger(__name__)


class ProblemListView(APIView):
    """Problem list and search endpoint with async DynamoDB backend"""
    permission_classes = [AllowAny]

    async def get(self, request):
        """
        Get problems with optional search and filtering

        Query params:
            platform: Filter by platform (optional)
            search: Search by title or problem_id (optional)
            page: Page number (optional)

        Returns:
            [
                {
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "problem_url": "...",
                    "tags": [...],
                    "language": "python",
                    "is_completed": true,
                    "needs_review": false,
                    "test_case_count": 5,
                    "created_at": "..."
                },
                ...
            ]
        """
        try:
            # Get query parameters
            platform = request.query_params.get('platform')
            search = request.query_params.get('search')

            problems = []

            # Async DynamoDB query using GSI3
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Query for completed problems using GSI3
                # GSI3PK = 'PROB#COMPLETED' for completed problems
                # GSI3SK = timestamp (sort key)
                response = await table.query(
                    IndexName='GSI3',
                    KeyConditionExpression='GSI3PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': 'PROB#COMPLETED'
                    },
                    ScanIndexForward=False,  # Newest first (descending by timestamp)
                    Limit=1000
                )

                problems = response.get('Items', [])

            # Filter out deleted problems (dat.del field)
            problems = [p for p in problems if not p.get('dat', {}).get('del', False)]

            # Extract platform and problem_id from PK
            # PK format: PROB#<platform>#<problem_id>
            for problem in problems:
                pk_parts = problem['PK'].split('#')
                if len(pk_parts) >= 3:
                    problem['platform'] = pk_parts[1]
                    problem['problem_id'] = '#'.join(pk_parts[2:])  # Handle IDs with # in them

            # Filter by platform if specified
            if platform:
                problems = [p for p in problems if p.get('platform') == platform]

            # Search by title or problem_id (case-insensitive)
            # Note: dat.tit is the title field in the compact storage format
            if search:
                search_lower = search.lower()
                problems = [
                    p for p in problems
                    if search_lower in p.get('dat', {}).get('tit', '').lower() or
                       search_lower in p.get('problem_id', '').lower()
                ]

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            for problem in problems:
                dat = problem.get('dat', {})
                # Convert Unix timestamp to ISO format for frontend
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('crt', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': dat.get('tit', ''),
                    'problem_url': dat.get('url', ''),
                    'tags': dat.get('tag', []),
                    'language': dat.get('lng', ''),
                    'is_completed': dat.get('cmp', False),
                    'needs_review': dat.get('nrv', False),
                    'test_case_count': dat.get('tcc', 0),  # Use denormalized count
                    'created_at': created_at_iso
                })

            # Sort by created_at descending (most recent first)
            # ISO format strings can be sorted lexicographically
            result.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching problem list: {e}")
            return Response(
                {'error': f'Failed to fetch problem list: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemDetailView(APIView):
    """Problem detail endpoint - Admin only"""
    permission_classes = [IsAuthenticated]

    async def get(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Get problem with test cases (Admin only)

        Returns:
            {
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "problem_url": "...",
                "tags": [...],
                "solution_code": "...",
                "language": "python",
                "constraints": "...",
                "is_completed": true,
                "needs_review": false,
                "verified_by_admin": false,
                "created_at": "...",
                "test_cases": [
                    {
                        "id": "1",
                        "input": "1 2",
                        "output": "3"
                    },
                    ...
                ]
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
            if not platform or not problem_identifier:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Async DynamoDB operations
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
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                problem = problem_response['Item']

                # Check if problem is deleted
                if problem.get('is_deleted', False):
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Get test cases
                testcases_response = await table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    ExpressionAttributeValues={
                        ':pk': f'PROB#{platform}#{problem_identifier}',
                        ':sk': 'TESTCASE#'
                    }
                )

                test_cases = testcases_response.get('Items', [])

            # Extract platform and problem_id from PK
            # PK format: PROB#<platform>#<problem_id>
            pk_parts = problem['PK'].split('#')
            parsed_platform = pk_parts[1] if len(pk_parts) >= 3 else platform
            parsed_problem_id = '#'.join(pk_parts[2:]) if len(pk_parts) >= 3 else problem_identifier

            # Extract data from compact storage format (dat field)
            dat = problem.get('dat', {})

            # Parse timestamps
            created_timestamp = problem.get('crt', 0)
            if isinstance(created_timestamp, Decimal):
                created_timestamp = float(created_timestamp)
            created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

            # Decode solution code if it exists (stored as base64)
            solution_code = dat.get('sol', '')
            if solution_code:
                try:
                    import base64
                    solution_code = base64.b64decode(solution_code).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to decode solution code: {e}")
                    solution_code = ''

            response_data = {
                'platform': parsed_platform,
                'problem_id': parsed_problem_id,
                'title': dat.get('tit', ''),
                'problem_url': dat.get('url', ''),
                'tags': dat.get('tag', []),
                'solution_code': solution_code,
                'language': dat.get('lng', ''),
                'constraints': dat.get('con', ''),
                'is_completed': dat.get('cmp', False),
                'needs_review': dat.get('nrv', False),
                'review_notes': dat.get('met', {}).get('review_notes'),
                'verified_by_admin': dat.get('vrf', False),
                'reviewed_at': dat.get('met', {}).get('reviewed_at'),
                'metadata': dat.get('met', {}),
                'created_at': created_at_iso,
                'test_cases': [
                    {
                        'id': tc.get('testcase_id', tc.get('SK', '').split('#')[-1]),
                        'input': tc.get('input', ''),
                        'output': tc.get('output', '')
                    }
                    for tc in test_cases
                ],
                'test_case_count': len(test_cases)
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching problem: {e}")
            return Response(
                {'error': f'Failed to fetch problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def delete(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Delete a problem (Admin only, hard delete immediately)

        Returns:
            {"message": "Problem deleted successfully"}
        """
        logger.info(f"[DELETE] Request from user: {request.user}, authenticated: {request.user.is_authenticated}")

        # Check if user is admin
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
            user_email = await sync_to_async(lambda: request.user.email)()
            logger.info(f"[DELETE] User email: {user_email}, is_admin: {is_admin}")
        except (AttributeError, Exception) as e:
            logger.warning(f"[DELETE] Error checking admin status: {e}")
            is_admin = False

        if not is_admin:
            logger.warning(f"[DELETE] Access denied - user is not admin")
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Validate parameters
            if not platform or not problem_identifier:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Attempting to hard delete problem: platform={platform}, problem_id={problem_identifier}")

            # Async DynamoDB operations
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Check if problem exists
                problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_identifier}',
                        'SK': 'META'
                    }
                )

                if 'Item' not in problem_response:
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                logger.info(f"Problem found, proceeding with hard delete")

                pk = f'PROB#{platform}#{problem_identifier}'

                # Delete all test cases first
                testcases_response = await table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    ExpressionAttributeValues={
                        ':pk': pk,
                        ':sk': 'TESTCASE#'
                    }
                )

                test_cases = testcases_response.get('Items', [])
                logger.info(f"Found {len(test_cases)} test cases to delete")

                # Delete test cases in parallel
                for tc in test_cases:
                    await table.delete_item(
                        Key={
                            'PK': tc['PK'],
                            'SK': tc['SK']
                        }
                    )

                logger.info(f"Deleted {len(test_cases)} test cases")

                # Delete the problem metadata
                await table.delete_item(
                    Key={
                        'PK': pk,
                        'SK': 'META'
                    }
                )

                logger.info(f"Hard delete completed successfully for {platform}/{problem_identifier}")

            # Invalidate caches - async
            await sync_to_async(cache.delete)("problem_drafts:all")
            await sync_to_async(cache.delete)("problem_registered:all")
            logger.info(f"[DELETE] Cache invalidated for problem_drafts:all and problem_registered:all")

            return Response(
                {'message': 'Problem deleted successfully'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error deleting problem: {e}")
            return Response(
                {'error': f'Failed to delete problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def post(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Update problem samples and solution code
        Admin only - requires authentication

        Request body:
            {
                "user_samples": [{"input": "...", "output": "..."}],
                "solution_code": "..."
            }

        Returns:
            {
                "message": "Problem updated successfully",
                "problem": {...}
            }
        """
        # Check admin permission
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
            user_email = await sync_to_async(lambda: request.user.email)()
        except (AttributeError, Exception):
            is_admin = False
            user_email = None

        if not is_admin:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Validate parameters
            if not platform or not problem_identifier:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_samples = request.data.get('user_samples', [])
            solution_code = request.data.get('solution_code')

            # Async DynamoDB operations
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Check if problem exists
                problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_identifier}',
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
                metadata = dat.get('met', {})

                # Prepare update expressions
                update_parts = []
                expr_values = {}

                # Update user samples in metadata
                if user_samples is not None:
                    metadata['user_samples'] = user_samples
                    dat['met'] = metadata
                    update_parts.append('dat.met = :metadata')
                    expr_values[':metadata'] = metadata

                # Update solution code (encode as base64)
                if solution_code is not None:
                    import base64
                    encoded_solution = base64.b64encode(solution_code.encode('utf-8')).decode('utf-8')
                    update_parts.append('dat.sol = :solution')
                    expr_values[':solution'] = encoded_solution

                if not update_parts:
                    return Response(
                        {'error': 'No valid fields to update provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update in DynamoDB
                update_expression = 'SET ' + ', '.join(update_parts)
                await table.update_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_identifier}',
                        'SK': 'META'
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expr_values
                )

                logger.info(f"Admin {user_email} updated problem {platform}#{problem_identifier}: samples={len(user_samples) if user_samples else 0}, solution_code={bool(solution_code)}")

                # Invalidate caches
                await sync_to_async(cache.delete)("problem_drafts:all")
                await sync_to_async(cache.delete)("problem_registered:all")

                # Get updated problem with test cases
                updated_problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_identifier}',
                        'SK': 'META'
                    }
                )
                updated_problem = updated_problem_response['Item']

                # Get test cases
                testcases_response = await table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    ExpressionAttributeValues={
                        ':pk': f'PROB#{platform}#{problem_identifier}',
                        ':sk': 'TESTCASE#'
                    }
                )
                test_cases = testcases_response.get('Items', [])

                # Extract platform and problem_id from PK
                pk_parts = updated_problem['PK'].split('#')
                parsed_platform = pk_parts[1] if len(pk_parts) >= 3 else platform
                parsed_problem_id = '#'.join(pk_parts[2:]) if len(pk_parts) >= 3 else problem_identifier

                # Extract data from compact storage format
                updated_dat = updated_problem.get('dat', {})

                # Format response
                created_timestamp = updated_problem.get('crt', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                # Decode solution code if exists
                decoded_solution_code = updated_dat.get('sol', '')
                if decoded_solution_code:
                    try:
                        import base64
                        decoded_solution_code = base64.b64decode(decoded_solution_code).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Failed to decode solution code: {e}")
                        decoded_solution_code = ''

                response_data = {
                    'platform': parsed_platform,
                    'problem_id': parsed_problem_id,
                    'title': updated_dat.get('tit', ''),
                    'problem_url': updated_dat.get('url', ''),
                    'tags': updated_dat.get('tag', []),
                    'solution_code': decoded_solution_code,
                    'language': updated_dat.get('lng', ''),
                    'constraints': updated_dat.get('con', ''),
                    'is_completed': updated_dat.get('cmp', False),
                    'needs_review': updated_dat.get('nrv', False),
                    'verified_by_admin': updated_dat.get('vrf', False),
                    'metadata': updated_dat.get('met', {}),
                    'created_at': created_at_iso,
                    'test_cases': [
                        {
                            'id': tc.get('testcase_id', tc.get('SK', '').split('#')[-1]),
                            'input': tc.get('input', ''),
                            'output': tc.get('output', '')
                        }
                        for tc in test_cases
                    ],
                    'test_case_count': len(test_cases)
                }

                return Response(
                    {
                        'message': 'Problem updated successfully',
                        'problem': response_data
                    },
                    status=status.HTTP_200_OK
                )

        except Exception as e:
            logger.error(f"Error updating problem: {e}")
            return Response(
                {'error': f'Failed to update problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def patch(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Update problem (currently supports marking as complete)
        Admin only - requires authentication

        Request body:
            {
                "is_completed": true  // Mark problem as completed
            }

        Returns:
            {
                "message": "Problem marked as completed",
                "problem": {...}
            }
        """
        # Check admin permission - async
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
            user_email = await sync_to_async(lambda: request.user.email)()
        except (AttributeError, Exception):
            is_admin = False
            user_email = None

        if not is_admin:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Validate parameters
            if not platform or not problem_identifier:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Async DynamoDB operations
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Check if problem exists
                problem_response = await table.get_item(
                    Key={
                        'PK': f'PROB#{platform}#{problem_identifier}',
                        'SK': 'META'
                    }
                )

                if 'Item' not in problem_response:
                    return Response(
                        {'error': 'Problem not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Update is_completed if provided
                is_completed = request.data.get('is_completed')
                if is_completed is not None:
                    # Update in DynamoDB - async
                    await table.update_item(
                        Key={
                            'PK': f'PROB#{platform}#{problem_identifier}',
                            'SK': 'META'
                        },
                        UpdateExpression='SET is_completed = :completed',
                        ExpressionAttributeValues={
                            ':completed': bool(is_completed)
                        }
                    )

                    message = 'Problem marked as completed' if is_completed else 'Problem marked as draft'
                    logger.info(f"Admin {user_email} updated problem {platform}#{problem_identifier}: is_completed={is_completed}")

                    # Invalidate caches - async
                    await sync_to_async(cache.delete)("problem_drafts:all")
                    await sync_to_async(cache.delete)("problem_registered:all")

                    # Get updated problem with test cases - async
                    updated_problem_response = await table.get_item(
                        Key={
                            'PK': f'PROB#{platform}#{problem_identifier}',
                            'SK': 'META'
                        }
                    )
                    updated_problem = updated_problem_response['Item']

                    # Get test cases
                    testcases_response = await table.query(
                        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                        ExpressionAttributeValues={
                            ':pk': f'PROB#{platform}#{problem_identifier}',
                            ':sk': 'TESTCASE#'
                        }
                    )
                    test_cases = testcases_response.get('Items', [])

                    # Extract platform and problem_id from PK
                    pk_parts = updated_problem['PK'].split('#')
                    parsed_platform = pk_parts[1] if len(pk_parts) >= 3 else platform
                    parsed_problem_id = '#'.join(pk_parts[2:]) if len(pk_parts) >= 3 else problem_identifier

                    # Extract data from compact storage format
                    dat = updated_problem.get('dat', {})

                    # Format response
                    created_timestamp = updated_problem.get('crt', 0)
                    if isinstance(created_timestamp, Decimal):
                        created_timestamp = float(created_timestamp)
                    created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                    # Decode solution code if exists
                    solution_code = dat.get('sol', '')
                    if solution_code:
                        try:
                            import base64
                            solution_code = base64.b64decode(solution_code).decode('utf-8')
                        except Exception as e:
                            logger.warning(f"Failed to decode solution code: {e}")
                            solution_code = ''

                    response_data = {
                        'platform': parsed_platform,
                        'problem_id': parsed_problem_id,
                        'title': dat.get('tit', ''),
                        'problem_url': dat.get('url', ''),
                        'tags': dat.get('tag', []),
                        'solution_code': solution_code,
                        'language': dat.get('lng', ''),
                        'constraints': dat.get('con', ''),
                        'is_completed': dat.get('cmp', False),
                        'needs_review': dat.get('nrv', False),
                        'verified_by_admin': dat.get('vrf', False),
                        'created_at': created_at_iso,
                        'test_cases': [
                            {
                                'id': tc.get('testcase_id', tc.get('SK', '').split('#')[-1]),
                                'input': tc.get('input', ''),
                                'output': tc.get('output', '')
                            }
                            for tc in test_cases
                        ],
                        'test_case_count': len(test_cases)
                    }

                    return Response(
                        {
                            'message': message,
                            'problem': response_data
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'error': 'No valid fields to update provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        except Exception as e:
            logger.error(f"Error updating problem: {e}")
            return Response(
                {'error': f'Failed to update problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemDraftsView(APIView):
    """Drafts (problems with no test cases or not completed) - Admin only - with caching"""
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get all draft problems (is_completed=False)
        Admin only.

        Returns:
            {
                "drafts": [...]
            }
        """
        # Check admin permission - async
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
        except (AttributeError, Exception):
            is_admin = False

        if not is_admin:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        cache_key = "problem_drafts:all"

        # Try to get from cache - async
        cached_data = await sync_to_async(cache.get)(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            problems = []

            # Async DynamoDB query using GSI3
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Query for draft problems using GSI3
                # GSI3PK = 'PROB#DRAFT' for draft problems
                # GSI3SK = timestamp (sort key)
                response = await table.query(
                    IndexName='GSI3',
                    KeyConditionExpression='GSI3PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': 'PROB#DRAFT'
                    },
                    ScanIndexForward=False,  # Newest first (descending by timestamp)
                    Limit=1000
                )

                problems = response.get('Items', [])

            # Filter out deleted problems (dat.del field)
            problems = [p for p in problems if not p.get('dat', {}).get('del', False)]

            # Extract platform and problem_id from PK
            # PK format: PROB#<platform>#<problem_id>
            for problem in problems:
                pk_parts = problem['PK'].split('#')
                if len(pk_parts) >= 3:
                    problem['platform'] = pk_parts[1]
                    problem['problem_id'] = '#'.join(pk_parts[2:])  # Handle IDs with # in them

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            for problem in problems:
                dat = problem.get('dat', {})
                # Convert timestamp to ISO format
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('crt', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': dat.get('tit', ''),
                    'problem_url': dat.get('url', ''),
                    'tags': dat.get('tag', []),
                    'language': dat.get('lng', ''),
                    'is_completed': dat.get('cmp', False),
                    'needs_review': dat.get('nrv', False),
                    'test_case_count': dat.get('tcc', 0),  # Use denormalized count
                    'created_at': created_at_iso
                })

            response_data = {'drafts': result}

            # Cache the result (shorter TTL for drafts as they change more frequently) - async
            ttl = settings.CACHE_TTL.get('SHORT', 60)
            await sync_to_async(cache.set)(cache_key, response_data, ttl)
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching drafts: {e}")
            return Response(
                {'error': f'Failed to fetch drafts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemRegisteredView(APIView):
    """Registered problems (problems with test cases and completed) - Admin only - with caching"""
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get all registered problems (is_completed=True)
        Admin only.

        Returns:
            {
                "problems": [...]
            }
        """
        # Check admin permission - async
        try:
            is_admin = await sync_to_async(lambda: request.user.is_admin())()
        except (AttributeError, Exception):
            is_admin = False

        if not is_admin:
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        cache_key = "problem_registered:all"

        # Try to get from cache - async
        cached_data = await sync_to_async(cache.get)(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            problems = []

            # Async DynamoDB query using GSI3
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)

                # Query for completed problems using GSI3
                # GSI3PK = 'PROB#COMPLETED' for completed problems
                # GSI3SK = timestamp (sort key)
                response = await table.query(
                    IndexName='GSI3',
                    KeyConditionExpression='GSI3PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': 'PROB#COMPLETED'
                    },
                    ScanIndexForward=False,  # Newest first (descending by timestamp)
                    Limit=1000
                )

                problems = response.get('Items', [])

            # Filter out deleted problems (dat.del field)
            problems = [p for p in problems if not p.get('dat', {}).get('del', False)]

            # Extract platform and problem_id from PK
            # PK format: PROB#<platform>#<problem_id>
            for problem in problems:
                pk_parts = problem['PK'].split('#')
                if len(pk_parts) >= 3:
                    problem['platform'] = pk_parts[1]
                    problem['problem_id'] = '#'.join(pk_parts[2:])  # Handle IDs with # in them

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            for problem in problems:
                dat = problem.get('dat', {})
                # Convert timestamp to ISO format
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('crt', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': dat.get('tit', ''),
                    'problem_url': dat.get('url', ''),
                    'tags': dat.get('tag', []),
                    'language': dat.get('lng', ''),
                    'is_completed': dat.get('cmp', False),
                    'needs_review': dat.get('nrv', False),
                    'verified_by_admin': dat.get('vrf', False),
                    'test_case_count': dat.get('tcc', 0),  # Use denormalized count
                    'created_at': created_at_iso
                })

            response_data = {'problems': result}

            # Cache the result - async
            ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)
            await sync_to_async(cache.set)(cache_key, response_data, ttl)
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching registered problems: {e}")
            return Response(
                {'error': f'Failed to fetch registered problems: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
