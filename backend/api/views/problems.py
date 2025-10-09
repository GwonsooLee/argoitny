"""Problem Views with DynamoDB Backend"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from decimal import Decimal
from ..dynamodb.client import DynamoDBClient
from ..dynamodb.repositories import ProblemRepository, SearchHistoryRepository
import logging

logger = logging.getLogger(__name__)


class ProblemListView(APIView):
    """Problem list and search endpoint with DynamoDB backend"""
    permission_classes = [AllowAny]

    def get(self, request):
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

            # Initialize repository
            problem_repo = ProblemRepository()

            # Get completed problems from DynamoDB (now returns tuple)
            problems, _ = problem_repo.list_completed_problems(limit=1000)

            # Filter by platform if specified
            if platform:
                problems = [p for p in problems if p['platform'] == platform]

            # Search by title or problem_id (case-insensitive)
            if search:
                search_lower = search.lower()
                problems = [
                    p for p in problems
                    if search_lower in p.get('title', '').lower() or
                       search_lower in p.get('problem_id', '').lower()
                ]

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            from datetime import datetime
            from decimal import Decimal
            for problem in problems:
                # Convert Unix timestamp to ISO format for frontend
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('created_at', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': problem['title'],
                    'problem_url': problem.get('problem_url', ''),
                    'tags': problem.get('tags', []),
                    'language': problem.get('language', ''),
                    'is_completed': problem.get('is_completed', False),
                    'test_case_count': problem.get('test_case_count', 0),  # Use denormalized count
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

    def get(self, request, problem_id=None, platform=None, problem_identifier=None):
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
                "created_at": "...",
                "test_cases": [
                    {
                        "testcase_id": "1",
                        "input": "1 2",
                        "output": "3"
                    },
                    ...
                ]
            }
        """
        # Check if user is admin
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            problem_repo = ProblemRepository()

            # Fetch from DynamoDB
            if platform and problem_identifier:
                problem = problem_repo.get_problem_with_testcases(
                    platform=platform,
                    problem_id=problem_identifier
                )
            else:
                # If only problem_id is provided, we need to scan (inefficient)
                # This is a legacy endpoint - should use platform + problem_id
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Format response to match serializer output
            response_data = {
                'platform': problem['platform'],
                'problem_id': problem['problem_id'],
                'title': problem['title'],
                'problem_url': problem.get('problem_url', ''),
                'tags': problem.get('tags', []),
                'solution_code': problem.get('solution_code', ''),
                'language': problem.get('language', ''),
                'constraints': problem.get('constraints', ''),
                'is_completed': problem.get('is_completed', False),
                'needs_review': problem.get('needs_review', False),
                'review_notes': problem.get('review_notes'),
                'verified_by_admin': problem.get('verified_by_admin', False),
                'reviewed_at': problem.get('reviewed_at'),
                'metadata': problem.get('metadata', {}),
                'created_at': (lambda ts: datetime.fromtimestamp(float(ts) if isinstance(ts, Decimal) else ts).isoformat() if ts else None)(problem.get('created_at', 0)),
                'test_cases': [
                    {
                        'id': tc['testcase_id'],
                        'input': tc['input'],
                        'output': tc['output']
                    }
                    for tc in problem.get('test_cases', [])
                ],
                'test_case_count': len(problem.get('test_cases', []))
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching problem: {e}")
            return Response(
                {'error': f'Failed to fetch problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Delete a problem (Admin only, soft delete for completed problems)

        Returns:
            {"message": "Problem deleted successfully"}
        """
        logger.info(f"[DELETE] Request from user: {request.user}, authenticated: {request.user.is_authenticated}")
        logger.info(f"[DELETE] User email: {getattr(request.user, 'email', None)}, is_admin: {request.user.is_admin() if request.user.is_authenticated else False}")

        # Check if user is admin
        if not request.user.is_admin():
            logger.warning(f"[DELETE] Access denied - user is not admin")
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            problem_repo = ProblemRepository()

            # Support both /problems/:id/ and /problems/:platform/:problem_id/
            if platform and problem_identifier:
                logger.info(f"Attempting to delete problem: platform={platform}, problem_id={problem_identifier}")

                # Check if problem exists
                problem = problem_repo.get_problem(
                    platform=platform,
                    problem_id=problem_identifier
                )
                logger.info(f"Problem found: {problem is not None}")
            else:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Use soft delete to avoid GSI consistency issues
            # Hard delete causes the item to still appear in GSI queries for a few seconds
            import time
            logger.info(f"Marking problem as deleted (soft delete): platform={platform}, problem_id={problem_identifier}")
            updated_problem = problem_repo.update_problem(
                platform=platform,
                problem_id=problem_identifier,
                updates={
                    'is_deleted': True,
                    'deleted_at': int(time.time()),
                    'deleted_reason': f'Deleted by admin {request.user.email}'
                }
            )
            success = updated_problem is not None
            logger.info(f"Soft delete result: {success}")

            if success:
                # Invalidate caches
                cache.delete("problem_drafts:all")
                cache.delete("problem_registered:all")
                logger.info(f"[DELETE] Cache invalidated for problem_drafts:all and problem_registered:all")

                # Verify cache was deleted
                if cache.get("problem_drafts:all") is not None:
                    logger.warning(f"[DELETE] Cache problem_drafts:all still exists after delete!")
                if cache.get("problem_registered:all") is not None:
                    logger.warning(f"[DELETE] Cache problem_registered:all still exists after delete!")

                # Schedule hard delete task (async, delayed by 5 seconds)
                from ..tasks import hard_delete_problem_task
                hard_delete_problem_task.apply_async(
                    kwargs={
                        'platform': platform,
                        'problem_id': problem_identifier
                    },
                    countdown=5,  # Wait 5 seconds before hard delete
                    queue='default'
                )
                logger.info(f"[DELETE] Scheduled hard delete task for {platform}/{problem_identifier}")

                return Response(
                    {'message': 'Problem deleted successfully'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Failed to delete problem'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Error deleting problem: {e}")
            return Response(
                {'error': f'Failed to delete problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, problem_id=None, platform=None, problem_identifier=None):
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
        # Check admin permission
        if not request.user.is_authenticated or not request.user.is_admin():
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            problem_repo = ProblemRepository()

            # Get problem
            if platform and problem_identifier:
                problem = problem_repo.get_problem(
                    platform=platform,
                    problem_id=problem_identifier
                )
            else:
                return Response(
                    {'error': 'Please provide both platform and problem_identifier'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update is_completed if provided
            is_completed = request.data.get('is_completed')
            if is_completed is not None:
                # Update in DynamoDB
                updated_problem = problem_repo.update_problem(
                    platform=platform,
                    problem_id=problem_identifier,
                    updates={'is_completed': bool(is_completed)}
                )

                message = 'Problem marked as completed' if is_completed else 'Problem marked as draft'
                logger.info(f"Admin {request.user.email} updated problem {platform}#{problem_identifier}: is_completed={is_completed}")

                # Invalidate caches
                cache.delete("problem_drafts:all")
                cache.delete("problem_registered:all")

                # Get updated problem with test cases
                updated_problem_full = problem_repo.get_problem_with_testcases(
                    platform=platform,
                    problem_id=problem_identifier
                )

                # Format response
                response_data = {
                    'platform': updated_problem_full['platform'],
                    'problem_id': updated_problem_full['problem_id'],
                    'title': updated_problem_full['title'],
                    'problem_url': updated_problem_full.get('problem_url', ''),
                    'tags': updated_problem_full.get('tags', []),
                    'solution_code': updated_problem_full.get('solution_code', ''),
                    'language': updated_problem_full.get('language', ''),
                    'constraints': updated_problem_full.get('constraints', ''),
                    'is_completed': updated_problem_full.get('is_completed', False),
                    'created_at': updated_problem_full.get('created_at'),
                    'test_cases': [
                        {
                            'id': tc['testcase_id'],
                            'input': tc['input'],
                            'output': tc['output']
                        }
                        for tc in updated_problem_full.get('test_cases', [])
                    ]
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

    def get(self, request):
        """
        Get all draft problems (is_completed=False)
        Admin only.

        Returns:
            {
                "drafts": [...]
            }
        """
        # Check admin permission
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        cache_key = "problem_drafts:all"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            # Initialize repository
            problem_repo = ProblemRepository()

            # Get draft problems from DynamoDB (now returns tuple)
            problems, _ = problem_repo.list_draft_problems(limit=1000)

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            from datetime import datetime
            from decimal import Decimal
            for problem in problems:
                # Convert timestamp to ISO format
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('created_at', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': problem['title'],
                    'problem_url': problem.get('problem_url', ''),
                    'tags': problem.get('tags', []),
                    'language': problem.get('language', ''),
                    'is_completed': problem.get('is_completed', False),
                    'needs_review': problem.get('needs_review', False),
                    'test_case_count': problem.get('test_case_count', 0),  # Use denormalized count
                    'created_at': created_at_iso
                })

            response_data = {'drafts': result}

            # Cache the result (shorter TTL for drafts as they change more frequently)
            ttl = settings.CACHE_TTL.get('SHORT', 60)
            cache.set(cache_key, response_data, ttl)
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

    def get(self, request):
        """
        Get all registered problems (is_completed=True)
        Admin only.

        Returns:
            {
                "problems": [...]
            }
        """
        # Check admin permission
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin permission required'},
                status=status.HTTP_403_FORBIDDEN
            )

        cache_key = "problem_registered:all"

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            # Initialize repository
            problem_repo = ProblemRepository()

            # Get completed problems from DynamoDB (now returns tuple)
            problems, _ = problem_repo.list_completed_problems(limit=1000)

            # Build result with denormalized test_case_count (no N+1 queries)
            result = []
            from datetime import datetime
            from decimal import Decimal
            for problem in problems:
                # Convert timestamp to ISO format
                # DynamoDB returns Decimal, convert to float first
                created_timestamp = problem.get('created_at', 0)
                if isinstance(created_timestamp, Decimal):
                    created_timestamp = float(created_timestamp)
                created_at_iso = datetime.fromtimestamp(created_timestamp).isoformat() if created_timestamp else None

                result.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': problem['title'],
                    'problem_url': problem.get('problem_url', ''),
                    'tags': problem.get('tags', []),
                    'language': problem.get('language', ''),
                    'is_completed': problem.get('is_completed', False),
                    'verified_by_admin': problem.get('verified_by_admin', False),
                    'test_case_count': problem.get('test_case_count', 0),  # Use denormalized count
                    'created_at': created_at_iso
                })

            response_data = {'problems': result}

            # Cache the result
            ttl = settings.CACHE_TTL.get('PROBLEM_LIST', 300)
            cache.set(cache_key, response_data, ttl)
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching registered problems: {e}")
            return Response(
                {'error': f'Failed to fetch registered problems: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
