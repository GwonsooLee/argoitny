"""Search History Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from ..models import SearchHistory
from ..serializers import SearchHistoryListSerializer, SearchHistorySerializer


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

            # Build queryset with optimized select_related
            # Only fetch user email field to minimize data transfer
            queryset = SearchHistory.objects.select_related('user').only(
                'id', 'user_id', 'user__email', 'user_identifier',
                'platform', 'problem_number', 'problem_title', 'language',
                'passed_count', 'failed_count', 'total_count',
                'is_code_public', 'created_at', 'code'
            )

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
