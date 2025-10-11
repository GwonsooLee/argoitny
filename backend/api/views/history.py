"""Search History Views - Async DynamoDB Implementation"""
import base64
import json
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.exceptions import ValidationError
from asgiref.sync import sync_to_async
from django.core.cache import cache

from api.dynamodb.async_client import AsyncDynamoDBClient
from api.dynamodb.async_repositories import AsyncSearchHistoryRepository
from ..tasks import generate_hints_task
from ..utils.rate_limit import check_rate_limit, log_usage


class SearchHistoryListView(APIView):
    """Search history list endpoint with cursor-based pagination"""
    permission_classes = [AllowAny]

    async def get(self, request):
        """
        Get search history with cursor-based pagination

        Query params:
            cursor: Pagination cursor (base64-encoded last_evaluated_key)
            limit: Number of items to fetch (default: 20, max: 100)
            my_only: Show only current user's history (default: false)
            task_id: Filter by specific Celery task ID (optional)

        Returns:
            {
                "results": [
                    {
                        "id": 1,
                        "user_email": "user@example.com",
                        "user_identifier": "user@example.com",
                        "platform": "baekjoon",
                        "problem_number": "1000",
                        "problem_title": "A+B",
                        "language": "python",
                        "passed_count": 95,
                        "failed_count": 5,
                        "total_count": 100,
                        "is_code_public": true,
                        "has_hints": false,
                        "created_at": "...",
                        "code": "..."  # Only if is_code_public is true
                    },
                    ...
                ],
                "next_cursor": "base64-encoded-cursor",
                "has_more": true
            }
        """
        try:
            # Get pagination params
            cursor_str = request.query_params.get('cursor')
            # Hard limit of 100 items per request
            limit = min(int(request.query_params.get('limit', 20)), 100)
            my_only = request.query_params.get('my_only', 'false').lower() == 'true'
            task_id = request.query_params.get('task_id')  # Optional task_id filter

            # Decode cursor if provided
            last_evaluated_key = None
            if cursor_str:
                try:
                    last_evaluated_key = json.loads(base64.b64decode(cursor_str).decode('utf-8'))
                except Exception:
                    return Response(
                        {'error': 'Invalid cursor parameter'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Initialize async DynamoDB repository
            # Note: AsyncSearchHistoryRepository wraps sync repository with sync_to_async
            # so we don't pass async table - let it create its own sync table
            history_repo = AsyncSearchHistoryRepository()

            # Fetch history based on filters
            if my_only:
                # Check if user is authenticated (sync operation)
                is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
                if is_authenticated:
                    # Show only current user's history
                    user_id = await sync_to_async(lambda: request.user.id)()
                    items, next_key = await history_repo.list_user_history(
                        user_id=user_id,
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )
                else:
                    # Return empty result if not authenticated
                    items = []
                    next_key = None
            else:
                # Show all public history + user's own private history
                is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
                if is_authenticated:
                    # Authenticated users: show their own history (public + private) + others' public history
                    # Strategy: Fetch both and merge
                    user_id = await sync_to_async(lambda: request.user.id)()

                    # Fetch user's own history (all items, public + private)
                    # Use a larger limit to get more items, we'll merge and limit later
                    # But cap at 100 to prevent excessive queries
                    user_items, _ = await history_repo.list_user_history(
                        user_id=user_id,
                        limit=min(limit * 2, 100),  # Cap at 100 items max
                        last_evaluated_key=None  # Start from beginning
                    )

                    # Fetch public history from others (time-partitioned)
                    # Query recent time partitions to avoid hot partition
                    from datetime import datetime, timedelta

                    public_items = []
                    hours_to_query = 24  # Query last 24 hours

                    for i in range(hours_to_query):
                        hour_time = datetime.now() - timedelta(hours=i)
                        hour_partition = hour_time.strftime('%Y%m%d%H')

                        items_batch, _ = await history_repo.list_public_history_by_partition(
                            partition=hour_partition,
                            limit=max(limit // hours_to_query, 5)  # Distribute limit across partitions
                        )
                        public_items.extend(items_batch)

                        # Stop early if we have enough items (cap at 100)
                        if len(public_items) >= min(limit * 2, 100):
                            break

                    # Merge: Remove duplicates (user's own public history appears in both queries)
                    # and sort by timestamp descending
                    seen_ids = set()
                    merged_items = []

                    for item in user_items + public_items:
                        item_id = item.get('PK')
                        if item_id not in seen_ids:
                            seen_ids.add(item_id)
                            merged_items.append(item)

                    # Sort by timestamp descending (newest first)
                    merged_items.sort(key=lambda x: x.get('crt', 0), reverse=True)

                    # Apply hard limit of 100 items max (most recent)
                    items = merged_items[:min(limit, 100)]
                    next_key = None  # Simplified: no pagination for merged results
                else:
                    # Anonymous users see only public history
                    items, next_key = await history_repo.list_public_history(
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )

            # Filter by task_id if provided
            if task_id:
                items = [item for item in items if item.get('dat', {}).get('tid') == task_id]

            # Transform DynamoDB items to serializer format
            import logging
            logger = logging.getLogger(__name__)

            results = []
            for item in items:
                try:
                    serialized = await self._transform_item_to_list_format(item, request)
                    results.append(serialized)
                    logger.info(f"[SearchHistory] Successfully transformed item: {item.get('PK')}")
                except Exception as e:
                    # Skip invalid items
                    logger.error(f"[SearchHistory] Failed to transform item {item.get('PK')}: {str(e)}", exc_info=True)
                    continue

            # Encode next cursor
            next_cursor = None
            has_more = False
            if next_key:
                next_cursor = base64.b64encode(json.dumps(next_key).encode('utf-8')).decode('utf-8')
                has_more = True

            logger.info(f"[SearchHistory] Returning {len(results)} transformed results")

            return Response({
                'results': results,
                'next_cursor': next_cursor,
                'has_more': has_more
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def _transform_item_to_list_format(self, item: dict, request) -> dict:
        """
        Transform DynamoDB item to SearchHistoryListSerializer format

        Args:
            item: DynamoDB item with structure:
                {
                    'PK': 'HIST#{id}',
                    'SK': 'META',
                    'tp': 'hist',
                    'dat': {
                        'uid': user_id,
                        'uidt': user_identifier,
                        'pid': problem_id,
                        'plt': platform,
                        'pno': problem_number,
                        'ptt': problem_title,
                        'lng': language,
                        'cod': code,
                        'res': result_summary,
                        'psc': passed_count,
                        'fsc': failed_count,
                        'toc': total_count,
                        'pub': is_code_public,
                        'trs': test_results (optional),
                        'hnt': hints (optional),
                        'met': metadata (optional)
                    },
                    'crt': created_timestamp,
                    'upd': updated_timestamp
                }
            request: Django request object

        Returns:
            Serialized item matching SearchHistoryListSerializer format
        """
        dat = item.get('dat', {})
        history_id = int(item['PK'].replace('HIST#', ''))

        # Extract user info
        user_email = None
        if 'uidt' in dat:
            user_email = dat['uidt']

        # Check if code should be visible
        is_public = dat.get('pub', False)
        is_owner = False

        # Check authentication and ownership (sync operations)
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        if is_authenticated:
            user_id = await sync_to_async(lambda: request.user.id)()
            user_email_current = await sync_to_async(lambda: request.user.email)()

            if dat.get('uid') == user_id:
                is_owner = True
            elif dat.get('uidt') == user_email_current:
                is_owner = True

        show_code = is_public or is_owner

        # Build serialized result
        result = {
            'id': history_id,
            'user_email': user_email,
            'user_identifier': dat.get('uidt'),
            'platform': dat.get('plt'),
            'problem_number': dat.get('pno'),
            'problem_title': dat.get('ptt'),
            'language': dat.get('lng'),
            'passed_count': dat.get('psc', 0),
            'failed_count': dat.get('fsc', 0),
            'total_count': dat.get('toc', 0),
            'is_code_public': is_public,
            'has_hints': bool(dat.get('hnt')),
            'created_at': self._format_timestamp(item.get('crt'))
        }

        # Include code only if visible
        if show_code:
            result['code'] = dat.get('cod')

        return result

    def _format_timestamp(self, timestamp: int) -> str:
        """
        Format Unix timestamp to ISO 8601 string

        Args:
            timestamp: Unix timestamp (can be int or Decimal from DynamoDB)

        Returns:
            ISO 8601 formatted datetime string
        """
        from datetime import datetime, timezone
        from decimal import Decimal

        if timestamp:
            # Convert Decimal to int if needed (DynamoDB returns Decimal for numbers)
            if isinstance(timestamp, Decimal):
                timestamp = int(timestamp)

            # Convert milliseconds to seconds if timestamp is too large
            if timestamp > 10000000000:  # > year 2286 in seconds means it's milliseconds
                timestamp = timestamp / 1000

            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat()
        return None


class SearchHistoryDetailView(APIView):
    """Search history detail endpoint - Owner only"""
    permission_classes = [IsAuthenticated]

    async def get(self, request, history_id):
        """
        Get detailed search history with full code (Owner only)

        Returns:
            {
                "id": 1,
                "user": 1,
                "user_email": "user@example.com",
                "user_identifier": "user@example.com",
                "problem": 1,
                "platform": "baekjoon",
                "problem_number": "1000",
                "problem_title": "A+B",
                "language": "python",
                "code": "...",  # Full code regardless of is_code_public
                "result_summary": "passed",
                "passed_count": 95,
                "failed_count": 5,
                "total_count": 100,
                "is_code_public": true,
                "test_results": [...],  # Enriched with input/expected
                "hints": [...],
                "created_at": "..."
            }
        """
        try:
            # Initialize async DynamoDB repository
            # Note: AsyncSearchHistoryRepository wraps sync repository with sync_to_async
            # so we don't pass async table - let it create its own sync table
            history_repo = AsyncSearchHistoryRepository()

            # Get history with test cases
            item = await history_repo.get_history_with_testcases(history_id)

            if not item:
                return Response(
                    {'error': 'History not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            dat = item.get('dat', {})

            # Verify ownership: Only the owner can view detailed history
            is_owner = False
            user_id = await sync_to_async(lambda: request.user.id)()
            user_email = await sync_to_async(lambda: request.user.email)()

            if dat.get('uid'):
                is_owner = dat['uid'] == user_id
            elif dat.get('uidt'):
                is_owner = dat['uidt'] == user_email

            if not is_owner:
                return Response(
                    {'error': 'Access denied. You can only view your own execution details.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Transform to serializer format
            result = self._transform_item_to_detail_format(item, history_id)

            # Enrich test_results with input and expected output from problem test cases
            if result.get('test_results') and result.get('platform') and result.get('problem_number'):
                result['test_results'] = await self._enrich_test_results(
                    result['test_results'],
                    result['platform'],
                    result['problem_number']
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _transform_item_to_detail_format(self, item: dict, history_id: int) -> dict:
        """
        Transform DynamoDB item to SearchHistorySerializer format

        Args:
            item: DynamoDB item
            history_id: History ID

        Returns:
            Serialized item matching SearchHistorySerializer format
        """
        dat = item.get('dat', {})

        result = {
            'id': history_id,
            'user': dat.get('uid'),
            'user_email': dat.get('uidt'),
            'user_identifier': dat.get('uidt'),
            'problem': dat.get('pid'),
            'platform': dat.get('plt'),
            'problem_number': dat.get('pno'),
            'problem_title': dat.get('ptt'),
            'language': dat.get('lng'),
            'code': dat.get('cod'),
            'result_summary': dat.get('res'),
            'passed_count': dat.get('psc', 0),
            'failed_count': dat.get('fsc', 0),
            'total_count': dat.get('toc', 0),
            'is_code_public': dat.get('pub', False),
            'test_results': dat.get('trs', []),
            'hints': dat.get('hnt', []),
            'created_at': self._format_timestamp(item.get('crt'))
        }

        return result

    async def _enrich_test_results(self, test_results: list, platform: str, problem_id: str) -> list:
        """
        Enrich test results with input and expected output from problem test cases

        Args:
            test_results: List of test result dictionaries with format:
                [{'tid': test_case_id, 'out': output, 'pas': passed, 'err': error, 'sts': status}, ...]
            platform: Platform name (e.g., 'baekjoon', 'leetcode')
            problem_id: Problem identifier

        Returns:
            Enriched test results with input and expected output
        """
        try:
            # Import repository
            from api.dynamodb.repositories.problem_repository import ProblemRepository

            # Get problem with test cases
            problem_repo = ProblemRepository()
            problem_data = await sync_to_async(problem_repo.get_problem_with_testcases)(
                platform=platform,
                problem_id=problem_id
            )

            if not problem_data:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Problem not found: {platform}/{problem_id}")
                # Return basic transformation without enrichment
                return [
                    {
                        'test_case_id': result.get('tid'),
                        'input': '',
                        'expected': '',
                        'output': result.get('out', ''),
                        'passed': result.get('pas', False),
                        'error': result.get('err'),
                        'status': result.get('sts', '')
                    }
                    for result in test_results
                ]

            # Create test case map: {testcase_id: {input, output}}
            test_case_map = {}
            for tc in problem_data.get('test_cases', []):
                test_case_map[tc['testcase_id']] = {
                    'input': tc['input'],
                    'expected': tc['output']
                }

            # Enrich test results with input and expected output
            enriched = []
            for result in test_results:
                tc_id = result.get('tid')
                tc_data = test_case_map.get(tc_id, {})

                enriched_result = {
                    'test_case_id': tc_id,
                    'input': tc_data.get('input', ''),
                    'expected': tc_data.get('expected', ''),
                    'output': result.get('out', ''),
                    'passed': result.get('pas', False),
                    'error': result.get('err'),
                    'status': result.get('sts', '')
                }
                enriched.append(enriched_result)

            return enriched

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to enrich test results: {str(e)}", exc_info=True)

            # Return basic transformation without enrichment
            return [
                {
                    'test_case_id': result.get('tid'),
                    'input': '',
                    'expected': '',
                    'output': result.get('out', ''),
                    'passed': result.get('pas', False),
                    'error': result.get('err'),
                    'status': result.get('sts', '')
                }
                for result in test_results
            ]

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp to ISO 8601 string"""
        from datetime import datetime, timezone
        from decimal import Decimal

        if timestamp:
            # Convert Decimal to int if needed (DynamoDB returns Decimal for numbers)
            if isinstance(timestamp, Decimal):
                timestamp = int(timestamp)

            # Convert milliseconds to seconds if timestamp is too large
            if timestamp > 10000000000:  # > year 2286 in seconds means it's milliseconds
                timestamp = timestamp / 1000

            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat()
        return None


class GenerateHintsView(APIView):
    """Generate hints for a failed code execution"""
    permission_classes = [IsAuthenticated]

    async def post(self, request, history_id):
        """
        Request hint generation for a specific execution

        Args:
            history_id: ID of the SearchHistory record

        Returns:
            {
                "task_id": "celery-task-id",
                "status": "PENDING",
                "message": "Hint generation started"
            }
        """
        # Check rate limit (disabled for now)
        # allowed, current_count, limit, message = await sync_to_async(check_rate_limit)(request.user, 'hint')
        # if not allowed:
        #     return Response(
        #         {
        #             'error': message,
        #             'current_count': current_count,
        #             'limit': limit
        #         },
        #         status=status.HTTP_429_TOO_MANY_REQUESTS
        #     )

        try:
            # Initialize async DynamoDB repository
            # Note: AsyncSearchHistoryRepository wraps sync repository with sync_to_async
            # so we don't pass async table - let it create its own sync table
            history_repo = AsyncSearchHistoryRepository()

            # Get the history record
            item = await history_repo.get_history(history_id)

            if not item:
                return Response(
                    {'error': 'History not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            dat = item.get('dat', {})

            # Check if there are failures
            if dat.get('fsc', 0) == 0:
                return Response(
                    {'error': 'No failed test cases - hints not needed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # If hints already exist, return them immediately
            if dat.get('hnt'):
                return Response({
                    'status': 'COMPLETED',
                    'hints': dat['hnt'],
                    'message': 'Hints already exist'
                }, status=status.HTTP_200_OK)

            # Start async task
            task = await sync_to_async(generate_hints_task.delay)(history_id)

            # Log usage for hint request
            await sync_to_async(log_usage)(
                user=request.user,
                action='hint',
                problem={'platform': dat.get('plt'), 'number': dat.get('pno')},
                metadata={'history_id': history_id, 'task_id': task.id, 'hint_type': 'code_analysis'}
            )

            return Response({
                'task_id': task.id,
                'status': 'PENDING',
                'message': 'Hint generation started'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response(
                {'error': f'Failed to start hint generation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetHintsView(APIView):
    """Get hints for a specific execution"""
    permission_classes = [AllowAny]

    async def get(self, request, history_id):
        """
        Get hints for a specific execution

        Returns:
            {
                "hints": ["hint1", "hint2", "hint3"],
                "status": "available" | "not_generated" | "not_needed"
            }
        """
        try:
            # Initialize async DynamoDB repository
            # Note: AsyncSearchHistoryRepository wraps sync repository with sync_to_async
            # so we don't pass async table - let it create its own sync table
            history_repo = AsyncSearchHistoryRepository()

            # Get the history record
            item = await history_repo.get_history(history_id)

            if not item:
                return Response(
                    {'error': 'History not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            dat = item.get('dat', {})

            # Check if there are failures
            if dat.get('fsc', 0) == 0:
                return Response({
                    'status': 'not_needed',
                    'message': 'No failed test cases'
                }, status=status.HTTP_200_OK)

            # Return hints if available
            hints = dat.get('hnt')
            if hints:
                return Response({
                    'status': 'available',
                    'hints': hints
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'not_generated',
                    'message': 'Hints have not been generated yet'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch hints: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
