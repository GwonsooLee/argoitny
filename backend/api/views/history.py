"""Search History Views - DynamoDB Implementation"""
import base64
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.exceptions import ValidationError

from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import SearchHistoryRepository
# DISABLED: from ..tasks import generate_hints_task
# DISABLED: from ..utils.rate_limit import check_rate_limit, log_usage


class SearchHistoryListView(APIView):
    """Search history list endpoint with cursor-based pagination"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get search history with cursor-based pagination

        Query params:
            cursor: Pagination cursor (base64-encoded last_evaluated_key)
            limit: Number of items to fetch (default: 20, max: 100)
            my_only: Show only current user's history (default: false)

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
            limit = min(int(request.query_params.get('limit', 20)), 100)
            my_only = request.query_params.get('my_only', 'false').lower() == 'true'

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

            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            history_repo = SearchHistoryRepository(table)

            # Fetch history based on filters
            if my_only:
                if request.user.is_authenticated:
                    # Show only current user's history
                    items, next_key = history_repo.list_user_history(
                        user_id=request.user.id,
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )
                else:
                    # Return empty result if not authenticated
                    items = []
                    next_key = None
            else:
                # For public timeline, always show public history
                # Note: User's own private history requires separate implementation
                # since we need to merge two queries (user history + public history)
                if request.user.is_authenticated:
                    # TODO: For authenticated users showing "my history + public history",
                    # we need to implement a merge strategy or use two separate queries.
                    # For now, we'll show public history only.
                    # To properly implement this, consider:
                    # 1. Query user's history separately
                    # 2. Query public history separately
                    # 3. Merge and sort by timestamp
                    items, next_key = history_repo.list_public_history(
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )
                else:
                    # Anonymous users see only public history
                    items, next_key = history_repo.list_public_history(
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )

            # Transform DynamoDB items to serializer format
            results = []
            for item in items:
                try:
                    serialized = self._transform_item_to_list_format(item, request)
                    results.append(serialized)
                except Exception as e:
                    # Skip invalid items
                    continue

            # Encode next cursor
            next_cursor = None
            has_more = False
            if next_key:
                next_cursor = base64.b64encode(json.dumps(next_key).encode('utf-8')).decode('utf-8')
                has_more = True

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

    def _transform_item_to_list_format(self, item: dict, request) -> dict:
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
        if request.user.is_authenticated:
            if dat.get('uid') == request.user.id:
                is_owner = True
            elif dat.get('uidt') == request.user.email:
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
            timestamp: Unix timestamp

        Returns:
            ISO 8601 formatted datetime string
        """
        from datetime import datetime, timezone
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat()
        return None


class SearchHistoryDetailView(APIView):
    """Search history detail endpoint - Owner only"""
    permission_classes = [IsAuthenticated]

    def get(self, request, history_id):
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
            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            history_repo = SearchHistoryRepository(table)

            # Get history with test cases
            item = history_repo.get_history_with_testcases(history_id)

            if not item:
                return Response(
                    {'error': 'History not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            dat = item.get('dat', {})

            # Verify ownership: Only the owner can view detailed history
            is_owner = False
            if dat.get('uid'):
                is_owner = dat['uid'] == request.user.id
            elif dat.get('uidt'):
                is_owner = dat['uidt'] == request.user.email

            if not is_owner:
                return Response(
                    {'error': 'Access denied. You can only view your own execution details.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Transform to serializer format
            result = self._transform_item_to_detail_format(item, history_id)

            # Enrich test_results with input and expected output from TestCase
            # Note: In DynamoDB, test results may already be embedded in the history
            # If we need to fetch from Django TestCase model, we can do it here
            if result.get('test_results'):
                result['test_results'] = self._enrich_test_results(result['test_results'])

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

    def _enrich_test_results(self, test_results: list) -> list:
        """
        Enrich test results with input and expected output from Django TestCase model

        Args:
            test_results: List of test result dictionaries

        Returns:
            Enriched test results
        """
        # Extract test case IDs
        test_case_ids = [tr['test_case_id'] for tr in test_results if 'test_case_id' in tr]

        if not test_case_ids:
            return test_results

        # Import Django model for test cases
        from ..models import TestCase

        # Fetch test cases efficiently
        test_cases = TestCase.objects.filter(id__in=test_case_ids).only('id', 'input', 'output').in_bulk()

        # Enrich results
        enriched = []
        for result in test_results:
            tc_id = result.get('test_case_id')
            if tc_id and tc_id in test_cases:
                tc = test_cases[tc_id]
                result['input'] = tc.input
                result['expected'] = tc.output
            enriched.append(result)

        return enriched

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp to ISO 8601 string"""
        from datetime import datetime, timezone
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.isoformat()
        return None


class GenerateHintsView(APIView):
    """Generate hints for a failed code execution"""
    permission_classes = [IsAuthenticated]

    def post(self, request, history_id):
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
        # Check rate limit
        allowed, current_count, limit, message = check_rate_limit(request.user, 'hint')
        if not allowed:
            return Response(
                {
                    'error': message,
                    'current_count': current_count,
                    'limit': limit
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        try:
            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            history_repo = SearchHistoryRepository(table)

            # Get the history record
            item = history_repo.get_history(history_id)

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
            task = generate_hints_task.delay(history_id)

            # Log usage
            # Note: problem reference might need to be fetched from Django if needed
            from ..models import Problem
            problem = None
            if dat.get('pid'):
                try:
                    problem = Problem.objects.get(id=dat['pid'])
                except Problem.DoesNotExist:
                    pass

            log_usage(
                user=request.user,
                action='hint',
                problem=problem,
                metadata={'history_id': history_id, 'task_id': task.id}
            )

            return Response({
                'task_id': task.id,
                'status': 'PENDING',
                'message': 'Hint generation started',
                'usage': {
                    'current_count': current_count + 1,
                    'limit': limit
                }
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response(
                {'error': f'Failed to start hint generation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetHintsView(APIView):
    """Get hints for a specific execution"""
    permission_classes = [AllowAny]

    def get(self, request, history_id):
        """
        Get hints for a specific execution

        Returns:
            {
                "hints": ["hint1", "hint2", "hint3"],
                "status": "available" | "not_generated" | "not_needed"
            }
        """
        try:
            # Initialize DynamoDB repository
            table = DynamoDBClient.get_table()
            history_repo = SearchHistoryRepository(table)

            # Get the history record
            item = history_repo.get_history(history_id)

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
