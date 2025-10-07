"""Problem Views with Caching"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Count
from ..models import Problem
from ..serializers import ProblemSerializer, ProblemListSerializer
from ..utils.cache import CacheKeyGenerator, get_or_set_cache
import logging

logger = logging.getLogger(__name__)


class ProblemListView(APIView):
    """Problem list and search endpoint with caching"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get problems with optional search

        Query params:
            platform: Filter by platform (optional)
            search: Search by title or problem_id (optional)
            page: Page number (optional)

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
        # Get query parameters
        platform = request.query_params.get('platform')
        search = request.query_params.get('search')
        page = request.query_params.get('page', 1)

        # Generate cache key
        cache_key = CacheKeyGenerator.problem_list_key(
            platform=platform,
            search=search,
            page=page
        )

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # Build queryset
        queryset = Problem.objects.minimal_fields().with_test_case_count().completed()

        # Filter by platform
        if platform:
            queryset = queryset.filter(platform=platform)

        # Search by title or problem_id
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(problem_id__icontains=search)
            )

        # Order by most recent
        queryset = queryset.order_by('-created_at')

        # Serialize data
        serializer = ProblemListSerializer(queryset, many=True)
        response_data = serializer.data

        # Cache the result
        ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)
        cache.set(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)


class ProblemDetailView(APIView):
    """Problem detail endpoint with caching"""
    permission_classes = [AllowAny]

    def get(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Get problem with test cases (cached)

        Returns:
            {
                "id": 1,
                "platform": "baekjoon",
                "problem_id": "1000",
                "title": "A+B",
                "created_at": "...",
                "test_cases": [...]
            }
        """
        # Generate cache key
        cache_key = CacheKeyGenerator.problem_detail_key(
            problem_id=problem_id,
            platform=platform,
            problem_identifier=problem_identifier
        )

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            # Fetch from database
            if platform and problem_identifier:
                problem = Problem.objects.with_test_cases().get(
                    platform=platform,
                    problem_id=problem_identifier
                )
            else:
                problem = Problem.objects.with_test_cases().get(id=problem_id)

            # Serialize data
            serializer = ProblemSerializer(problem)
            response_data = serializer.data

            # Cache the result
            ttl = settings.CACHE_TTL.get('PROBLEM_DETAIL', 600)
            cache.set(cache_key, response_data, ttl)
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return Response(response_data, status=status.HTTP_200_OK)

        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error fetching problem: {e}")
            return Response(
                {'error': f'Failed to fetch problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Delete a problem (invalidates caches automatically via signals)

        Returns:
            {"message": "Problem deleted successfully"}
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

            # Delete (signals will handle cache invalidation)
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
            logger.error(f"Error deleting problem: {e}")
            return Response(
                {'error': f'Failed to delete problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemDraftsView(APIView):
    """Drafts (problems with no test cases) - with caching"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all draft problems (is_completed=False)

        Returns:
            {
                "drafts": [...]
            }
        """
        cache_key = "problem_drafts:all"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # Build queryset
        queryset = Problem.objects.minimal_fields().with_test_case_count().drafts().order_by('-created_at')

        # Serialize data
        serializer = ProblemListSerializer(queryset, many=True)
        response_data = {'drafts': serializer.data}

        # Cache the result (shorter TTL for drafts as they change more frequently)
        ttl = settings.CACHE_TTL.get('SHORT', 60)
        cache.set(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)


class ProblemRegisteredView(APIView):
    """Registered problems (problems with test cases) - with caching"""
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get all registered problems (is_completed=True)

        Returns:
            {
                "problems": [...]
            }
        """
        cache_key = "problem_registered:all"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # Build queryset
        queryset = Problem.objects.minimal_fields().with_test_case_count().completed().order_by('-created_at')

        # Serialize data
        serializer = ProblemListSerializer(queryset, many=True)
        response_data = {'problems': serializer.data}

        # Cache the result
        ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)
        cache.set(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)
