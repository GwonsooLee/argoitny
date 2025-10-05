"""Problem Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from ..models import Problem
from ..serializers import ProblemSerializer, ProblemListSerializer


class ProblemListView(APIView):
    """Problem list and search endpoint"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get problems with optional search

        Query params:
            platform: Filter by platform (optional)
            search: Search by title or problem_id (optional)

        Returns:
            [
                {
                    "id": 1,
                    "platform": "baekjoon",
                    "problem_id": "1000",
                    "title": "A+B",
                    "created_at": "..."
                },
                ...
            ]
        """
        queryset = Problem.objects.all()

        # Filter by platform
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)

        # Search by title or problem_id
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(problem_id__icontains=search)
            )

        # Order by most recent
        queryset = queryset.order_by('-created_at')

        serializer = ProblemListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProblemDetailView(APIView):
    """Problem detail endpoint"""
    permission_classes = [AllowAny]

    def get(self, request, problem_id):
        """
        Get problem with test cases

        Returns:
            {
                "id": 1,
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "created_at": "...",
                "test_cases": [
                    {
                        "id": 1,
                        "input": "1 2",
                        "output": "3"
                    },
                    ...
                ]
            }
        """
        try:
            problem = Problem.objects.prefetch_related('test_cases').get(id=problem_id)
            serializer = ProblemSerializer(problem)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
