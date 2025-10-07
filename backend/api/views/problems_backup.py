"""Problem Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q, Count
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
        # OPTIMIZATION: Use custom manager methods for cleaner, more maintainable code
        # - minimal_fields(): fetches only needed fields
        # - with_test_case_count(): annotates test_case_count to avoid N+1
        # - completed(): filters only completed, non-deleted problems
        queryset = Problem.objects.minimal_fields().with_test_case_count().completed()

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

    def get(self, request, problem_id=None, platform=None, problem_identifier=None):
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
            # OPTIMIZATION: Use with_test_cases() custom manager method
            # This prefetches test_cases efficiently to avoid N+1 queries
            if platform and problem_identifier:
                problem = Problem.objects.with_test_cases().get(
                    platform=platform,
                    problem_id=problem_identifier
                )
            else:
                problem = Problem.objects.with_test_cases().get(id=problem_id)

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

    def delete(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Delete a problem

        Returns:
            {
                "message": "Problem deleted successfully"
            }
        """
        try:
            # Support both /problems/:id/ and /problems/:platform/:problem_id/
            if platform and problem_identifier:
                problem = Problem.objects.get(
                    platform=platform,
                    problem_id=problem_identifier
                )
            else:
                problem = Problem.objects.get(id=problem_id)

            problem.delete()
            return Response(
                {'message': 'Problem deleted successfully'},
                status=status.HTTP_200_OK
            )

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemDraftsView(APIView):
    """Drafts (problems with no test cases)"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all draft problems (is_completed=False)

        Returns:
            {
                "drafts": [
                    {
                        "id": 1,
                        "platform": "baekjoon",
                        "problem_id": "1000",
                        "title": "A+B",
                        "tags": [...],
                        "language": "python",
                        "created_at": "...",
                        "test_case_count": 0
                    },
                    ...
                ]
            }
        """
        # OPTIMIZATION: Use custom manager methods for cleaner code
        queryset = Problem.objects.minimal_fields().with_test_case_count().drafts().order_by('-created_at')

        serializer = ProblemListSerializer(queryset, many=True)
        return Response({'drafts': serializer.data}, status=status.HTTP_200_OK)


class ProblemRegisteredView(APIView):
    """Registered problems (problems with test cases)"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all registered problems (is_completed=True)

        Returns:
            {
                "problems": [
                    {
                        "id": 1,
                        "platform": "baekjoon",
                        "problem_id": "1000",
                        "title": "A+B",
                        "tags": [...],
                        "language": "python",
                        "created_at": "...",
                        "test_case_count": 10
                    },
                    ...
                ]
            }
        """
        # OPTIMIZATION: Use custom manager methods for cleaner code
        queryset = Problem.objects.minimal_fields().with_test_case_count().completed().order_by('-created_at')

        serializer = ProblemListSerializer(queryset, many=True)
        return Response({'problems': serializer.data}, status=status.HTTP_200_OK)
