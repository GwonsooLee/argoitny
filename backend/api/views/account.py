"""Account Views - Async Version"""
from rest_framework import status
from adrf.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..authentication import CustomJWTAuthentication
from django.conf import settings
from ..utils.serializer_helper import serialize_dynamodb_user
from ..dynamodb.async_client import AsyncDynamoDBClient
from ..dynamodb.async_repositories import (
    AsyncUserRepository,
    AsyncUsageLogRepository,
    AsyncSearchHistoryRepository,
    AsyncSubscriptionPlanRepository
)
from django.core.cache import cache
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import datetime, timedelta
from ..serializers import UserSerializer
from ..utils.cache import CacheKeyGenerator
import logging

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    """Get current user profile with latest plan information"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get current user's profile with up-to-date plan information

        Returns:
            User dict with latest subscription_plan_name from DynamoDB
        """
        try:
            # Get user email from JWT token (sync operation)
            user_email = await sync_to_async(lambda: request.user.email)()

            # Initialize async repository with aioboto3 table
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)
                user_repo = AsyncUserRepository(table)

                # Get user by email (from JWT token)
                user_dict = await user_repo.get_user_by_email(user_email)

                if not user_dict:
                    return Response(
                        {'error': 'User not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Serialize with latest plan information (sync operation)
            serialized_user = await sync_to_async(serialize_dynamodb_user)(user_dict)

            return Response(serialized_user, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error fetching user profile: {e}')
            return Response(
                {'error': f'Failed to fetch user profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccountStatsView(APIView):
    """Get user account statistics"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get user's test execution statistics (cached)

        Returns:
            {
                "total_executions": 100,
                "by_platform": {
                    "baekjoon": 60,
                    "codeforces": 40
                },
                "by_language": {
                    "python": 70,
                    "cpp": 20,
                    "java": 10
                },
                "total_problems": 25,
                "passed_executions": 80,
                "failed_executions": 20
            }
        """
        # Get user email (sync operation)
        user_email = await sync_to_async(lambda: request.user.email)()

        # Generate cache key using email
        cache_key = CacheKeyGenerator.user_stats_key(user_email)

        # Try to get from cache (sync operation)
        cached_data = await sync_to_async(cache.get)(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        try:
            # AsyncSearchHistoryRepository wraps sync repo with sync_to_async
            # so we don't pass async table - let it create its own sync table
            history_repo = AsyncSearchHistoryRepository()

            # Get all user history from DynamoDB
            # Note: This uses GSI1 (user_email index) to efficiently query user's history
            user_history_items, _ = await history_repo.list_user_history(
                user_id=user_email,  # user_id is email in DynamoDB
                limit=1000  # Get up to 1000 items (adjust if needed)
            )

            # Process statistics from items
            total_executions = len(user_history_items)

            # Count by platform
            by_platform = {}
            by_language = {}
            problem_ids = set()
            passed_count = 0
            failed_count = 0

            for item in user_history_items:
                dat = item.get('dat', {})

                # Count by platform
                platform = dat.get('plt')
                if platform:
                    by_platform[platform] = by_platform.get(platform, 0) + 1

                # Count by language
                language = dat.get('lng')
                if language:
                    by_language[language] = by_language.get(language, 0) + 1

                # Track unique problems (platform#problem_number)
                problem_number = dat.get('pno')
                if platform and problem_number:
                    problem_ids.add(f"{platform}#{problem_number}")

                # Count passed/failed
                failed = dat.get('fsc', 0)
                if failed == 0:
                    passed_count += 1
                else:
                    failed_count += 1

            response_data = {
                'total_executions': total_executions,
                'by_platform': by_platform,
                'by_language': by_language,
                'total_problems': len(problem_ids),
                'passed_executions': passed_count,
                'failed_executions': failed_count
            }

            # Cache the result (sync operation)
            ttl = settings.CACHE_TTL.get('USER_STATS', 180)
            await sync_to_async(cache.set)(cache_key, response_data, ttl)
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error calculating user stats: {e}')
            # Return empty stats on error
            return Response({
                'total_executions': 0,
                'by_platform': {},
                'by_language': {},
                'total_problems': 0,
                'passed_executions': 0,
                'failed_executions': 0
            }, status=status.HTTP_200_OK)


class UpdatePlanView(APIView):
    """Update user's subscription plan"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def patch(self, request):
        """
        Update user's subscription plan

        Request body:
            {
                "plan": "Free"  # Plan name: "Free", "Pro", "Pro+"
            }

        Returns:
            {
                "id": 1,
                "email": "user@example.com",
                "name": "User Name",
                "picture": "https://...",
                "is_admin": false,
                "subscription_plan_name": "Free",
                "subscription_plan_description": "Free plan with basic features",
                "created_at": "2025-01-01T00:00:00Z"
            }
        """
        # Get user email (sync operation)
        user_email = await sync_to_async(lambda: request.user.email)()
        plan_name = request.data.get('plan')

        if not plan_name:
            return Response(
                {'error': 'Plan name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize async repositories with aioboto3 table
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)
                plan_repo = AsyncSubscriptionPlanRepository(table)
                user_repo = AsyncUserRepository(table)

                # Get the plan from DynamoDB (must be active and not Admin plan)
                plans = await plan_repo.list_plans()
                plan = None
                for p in plans:
                    if (p.get('name') == plan_name and
                        p.get('is_active', False) and
                        p.get('name') != 'Admin'):
                        plan = p
                        break

                if not plan:
                    return Response(
                        {'error': 'Invalid plan name or plan not available'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Get current user to extract user_id
                current_user = await user_repo.get_user_by_email(user_email)
                if not current_user:
                    return Response(
                        {'error': 'User not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Update user's plan in DynamoDB using user_id
                await user_repo.update_user(
                    user_id=current_user['user_id'],
                    updates={'subscription_plan_id': plan['id']}
                )

                # Get updated user
                updated_user = await user_repo.get_user_by_email(user_email)

            # Clear user stats cache (sync operation)
            cache_key = CacheKeyGenerator.user_stats_key(user_email)
            await sync_to_async(cache.delete)(cache_key)

            # Serialize and return updated user info
            serialized_user = await sync_to_async(serialize_dynamodb_user)(updated_user)
            return Response(serialized_user, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error updating user plan: {e}')
            return Response(
                {'error': f'Failed to update plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlanUsageView(APIView):
    """Get user's plan usage statistics"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get user's current plan usage vs limits

        Returns:
            {
                "plan_name": "Free",
                "limits": {
                    "max_hints_per_day": 5,
                    "max_executions_per_day": 50,
                    "max_problems": 10
                },
                "usage": {
                    "hints_today": 3,
                    "executions_today": 25,
                    "total_problems": 7
                }
            }
        """
        # Get user email and subscription_plan_id (sync operations)
        user_email = await sync_to_async(lambda: request.user.email)()
        subscription_plan_id = await sync_to_async(lambda: request.user.subscription_plan_id)()

        # Default plan info
        plan_name = 'Free'
        limits = {
            'max_hints_per_day': 5,
            'max_executions_per_day': 50,
            'max_problems': -1,
        }

        # Get plan info from DynamoDB if user has a plan
        if subscription_plan_id:
            try:
                # Initialize async repository with aioboto3 table
                async with AsyncDynamoDBClient.get_resource() as resource:
                    table = await resource.Table(AsyncDynamoDBClient._table_name)
                    plan_repo = AsyncSubscriptionPlanRepository(table)
                    plan = await plan_repo.get_plan(subscription_plan_id)

                    if plan:
                        plan_name = plan.get('name', 'Free')
                        limits = {
                            'max_hints_per_day': plan.get('max_hints_per_day', 5),
                            'max_executions_per_day': plan.get('max_executions_per_day', 50),
                            'max_problems': plan.get('max_problems', -1),
                        }
            except Exception as e:
                logger.error(f'Failed to get plan info: {e}')

        # Generate cache key using email
        cache_key = CacheKeyGenerator.user_stats_key(user_email) + ':usage'

        # Try to get from cache (sync operation)
        cached_data = await sync_to_async(cache.get)(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # Calculate today's usage from DynamoDB
        try:
            # AsyncRepositories wrap sync repos with sync_to_async
            # so we don't pass async table - let them create their own sync tables
            usage_repo = AsyncUsageLogRepository()
            history_repo = AsyncSearchHistoryRepository()

            # Get today's date string
            today_str = datetime.utcnow().strftime('%Y%m%d')

            # Count hints and executions today
            hints_today = await usage_repo.get_daily_usage_count_by_email(
                user_email,
                'hint',
                today_str
            )
            executions_today = await usage_repo.get_daily_usage_count_by_email(
                user_email,
                'execution',
                today_str
            )

            # Count total unique problems
            total_problems = await history_repo.count_unique_problems(user_email)

        except Exception as e:
            logger.error(f'Failed to get usage statistics: {e}')
            hints_today = 0
            executions_today = 0
            total_problems = 0

        response_data = {
            'plan_name': plan_name,
            'limits': {
                'max_hints_per_day': limits['max_hints_per_day'],
                'max_executions_per_day': limits['max_executions_per_day'],
                'max_problems': limits['max_problems'],
            },
            'usage': {
                'hints_today': hints_today,
                'executions_today': executions_today,
                'total_problems': total_problems,
            }
        }

        # Cache the result for 60 seconds (shorter TTL for usage data) - sync operation
        ttl = 60
        await sync_to_async(cache.set)(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)
