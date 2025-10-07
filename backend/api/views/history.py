"""Search History Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from ..models import SearchHistory
from ..serializers import SearchHistoryListSerializer, SearchHistorySerializer, GenerateHintsSerializer
from ..tasks import generate_hints_task
from ..utils.rate_limit import check_rate_limit, log_usage


class SearchHistoryListView(APIView):
    """Search history list endpoint with smart pagination"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get search history with incremental pagination

        Query params:
            offset: Starting index (default: 0)
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
                        "created_at": "...",
                        "code": "..."  # Only if is_code_public is true
                    },
                    ...
                ],
                "count": 150,
                "next_offset": 20,
                "has_more": true
            }
        """
        try:
            # Get pagination params
            offset = int(request.query_params.get('offset', 0))
            limit = min(int(request.query_params.get('limit', 20)), 100)
            my_only = request.query_params.get('my_only', 'false').lower() == 'true'

            # OPTIMIZATION: Build queryset with optimized select_related and minimal fields
            # Use custom queryset methods for cleaner, more maintainable code
            queryset = SearchHistory.objects.with_user().minimal_fields()

            # Filter by user if my_only is true
            if my_only:
                if request.user.is_authenticated:
                    # Show only current user's history (both public and private)
                    # This query uses sh_user_created_idx composite index
                    queryset = queryset.filter(user=request.user)
                else:
                    # Return empty result if not authenticated
                    queryset = queryset.none()
            else:
                # Show user's own history (all) + public history from others
                if request.user.is_authenticated:
                    # My history (all) OR public history (including others')
                    # Uses sh_user_created_idx and sh_public_created_idx indexes
                    queryset = queryset.filter(
                        Q(user=request.user) | Q(is_code_public=True)
                    )
                else:
                    # Anonymous users see only public history
                    # This query uses sh_public_created_idx composite index
                    queryset = queryset.filter(is_code_public=True)

            # Get total count efficiently
            total_count = queryset.count()

            # Get paginated results
            results = queryset[offset:offset + limit]

            # Serialize with request context
            serializer = SearchHistoryListSerializer(results, many=True, context={'request': request})

            # Calculate next offset
            next_offset = offset + limit
            has_more = next_offset < total_count

            return Response({
                'results': serializer.data,
                'count': total_count,
                'next_offset': next_offset if has_more else None,
                'has_more': has_more
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {'error': 'Invalid offset or limit parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SearchHistoryDetailView(APIView):
    """Search history detail endpoint"""
    permission_classes = [AllowAny]

    def get(self, request, history_id):
        """
        Get detailed search history with full code

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
                "created_at": "..."
            }
        """
        try:
            from ..models import TestCase

            # Optimize: Use select_related to join user in a single query
            history = SearchHistory.objects.select_related('user').get(id=history_id)
            serializer = SearchHistorySerializer(history)
            data = serializer.data

            # Enrich test_results with input and expected output from TestCase
            if data.get('test_results'):
                test_case_ids = [tr['test_case_id'] for tr in data['test_results'] if 'test_case_id' in tr]

                # Optimize: Use only() to fetch only needed fields, use in_bulk for efficient lookup
                if test_case_ids:
                    test_cases = TestCase.objects.filter(id__in=test_case_ids).only('id', 'input', 'output').in_bulk()

                    for result in data['test_results']:
                        tc_id = result.get('test_case_id')
                        if tc_id and tc_id in test_cases:
                            tc = test_cases[tc_id]
                            result['input'] = tc.input
                            result['expected'] = tc.output

            return Response(data, status=status.HTTP_200_OK)

        except SearchHistory.DoesNotExist:
            return Response(
                {'error': 'History not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            # Verify the history record exists and has failures (optimized: only fetch needed fields)
            history = SearchHistory.objects.only(
                'id', 'failed_count', 'hints', 'problem_id'
            ).get(id=history_id)

            # Check if there are failures
            if history.failed_count == 0:
                return Response(
                    {'error': 'No failed test cases - hints not needed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # If hints already exist, return them immediately
            if history.hints:
                return Response({
                    'status': 'COMPLETED',
                    'hints': history.hints,
                    'message': 'Hints already exist'
                }, status=status.HTTP_200_OK)

            # Start async task
            task = generate_hints_task.delay(history_id)

            # Log usage
            log_usage(
                user=request.user,
                action='hint',
                problem_id=history.problem_id,
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

        except SearchHistory.DoesNotExist:
            return Response(
                {'error': 'History not found'},
                status=status.HTTP_404_NOT_FOUND
            )
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
            # Get the history record (optimized: only fetch needed fields)
            history = SearchHistory.objects.only(
                'id', 'failed_count', 'hints'
            ).get(id=history_id)

            # Check if there are failures
            if history.failed_count == 0:
                return Response({
                    'status': 'not_needed',
                    'message': 'No failed test cases'
                }, status=status.HTTP_200_OK)

            # Return hints if available
            if history.hints:
                return Response({
                    'status': 'available',
                    'hints': history.hints
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'not_generated',
                    'message': 'Hints have not been generated yet'
                }, status=status.HTTP_200_OK)

        except SearchHistory.DoesNotExist:
            return Response(
                {'error': 'History not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch hints: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
