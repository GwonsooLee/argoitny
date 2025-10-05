"""Search History Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
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

            # Get total count
            total_count = SearchHistory.objects.count()

            # Get paginated results (most recent first)
            queryset = SearchHistory.objects.select_related('user').order_by('-created_at')
            results = queryset[offset:offset + limit]

            # Serialize
            serializer = SearchHistoryListSerializer(results, many=True)

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
            history = SearchHistory.objects.select_related('user').get(id=history_id)
            serializer = SearchHistorySerializer(history)
            return Response(serializer.data, status=status.HTTP_200_OK)

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
