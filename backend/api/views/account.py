"""Account Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..authentication import CustomJWTAuthentication
from django.conf import settings
from ..utils.serializer_helper import serialize_dynamodb_user
from ..dynamodb.client import DynamoDBClient
from ..dynamodb.repositories import UserRepository
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from ..models import SearchHistory, SubscriptionPlan, Problem, UsageLog
from ..serializers import UserSerializer
from ..utils.cache import CacheKeyGenerator
import logging

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    """Get current user profile with latest plan information"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get current user's profile with up-to-date plan information

        Returns:
            User dict with latest subscription_plan_name from DynamoDB
        """
        try:
            # Get user from DynamoDB to ensure latest data
            table = DynamoDBClient.get_table()
            user_repo = UserRepository(table)

            # Get user by email (from JWT token)
            user_dict = user_repo.get_user_by_email(request.user.email)

            if not user_dict:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Serialize with latest plan information
            serialized_user = serialize_dynamodb_user(user_dict)

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

    def get(self, request):
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
        user = request.user

        # Generate cache key
        cache_key = CacheKeyGenerator.user_stats_key(user.id)

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # OPTIMIZATION: Use only() to fetch minimal fields for counting
        # This significantly reduces data transfer from database
        user_history = SearchHistory.objects.filter(user=user).only(
            'id', 'platform', 'language', 'problem_id', 'failed_count'
        )

        # OPTIMIZATION: Aggregate all stats in a single pass using database aggregations
        # Total executions (use count() which is optimized)
        total_executions = user_history.count()

        # OPTIMIZATION: Group by platform - single query with aggregation
        platform_stats = user_history.values('platform').annotate(count=Count('id')).order_by()
        by_platform = {stat['platform']: stat['count'] for stat in platform_stats}

        # OPTIMIZATION: Group by language - single query with aggregation
        language_stats = user_history.values('language').annotate(count=Count('id')).order_by()
        by_language = {stat['language']: stat['count'] for stat in language_stats}

        # OPTIMIZATION: Count unique problems - single query
        total_problems = user_history.values('problem').distinct().count()

        # OPTIMIZATION: Count passed/failed using conditional aggregation in a single query
        # This is much faster than two separate filter().count() calls
        pass_fail_stats = user_history.aggregate(
            passed=Count('id', filter=Q(failed_count=0)),
            failed=Count('id', filter=Q(failed_count__gt=0))
        )

        response_data = {
            'total_executions': total_executions,
            'by_platform': by_platform,
            'by_language': by_language,
            'total_problems': total_problems,
            'passed_executions': pass_fail_stats['passed'],
            'failed_executions': pass_fail_stats['failed']
        }

        # Cache the result
        ttl = settings.CACHE_TTL.get('USER_STATS', 180)
        cache.set(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)


class UpdatePlanView(APIView):
    """Update user's subscription plan"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
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
        user = request.user
        plan_name = request.data.get('plan')

        if not plan_name:
            return Response(
                {'error': 'Plan name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the plan (must be active and not Admin plan for regular users)
        plan = SubscriptionPlan.objects.filter(
            name=plan_name,
            is_active=True
        ).exclude(name='Admin').first()

        if not plan:
            return Response(
                {'error': 'Invalid plan name or plan not available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update user's plan
        user.subscription_plan = plan
        user.save()

        # Clear user stats cache
        cache_key = CacheKeyGenerator.user_stats_key(user.id)
        cache.delete(cache_key)

        # Return updated user info
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlanUsageView(APIView):
    """Get user's plan usage statistics"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
        user = request.user

        # Get plan name and limits from DynamoDB
        plan_name = 'Free'
        limits = {
            'max_hints_per_day': 5,
            'max_executions_per_day': 50,
            'max_problems': -1,
        }

        if user.subscription_plan_id:
            try:
                from ..dynamodb.client import DynamoDBClient
                from ..dynamodb.repositories import SubscriptionPlanRepository

                table = DynamoDBClient.get_table()
                plan_repo = SubscriptionPlanRepository(table)
                plan = plan_repo.get_plan(user.subscription_plan_id)

                if plan:
                    plan_name = plan.get('name', 'Free')
                    limits = {
                        'max_hints_per_day': plan.get('max_hints_per_day', 5),
                        'max_executions_per_day': plan.get('max_executions_per_day', 50),
                        'max_problems': plan.get('max_problems', -1),
                    }
            except Exception as e:
                logger.error(f'Failed to get plan info: {e}')

        # Generate cache key using email (user.id is email in DynamoDB)
        cache_key = CacheKeyGenerator.user_stats_key(user.email) + ':usage'

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key}")

        # Calculate today's usage from DynamoDB
        try:
            from ..dynamodb.repositories import UsageLogRepository, SearchHistoryRepository

            table = DynamoDBClient.get_table()
            usage_repo = UsageLogRepository(table)
            history_repo = SearchHistoryRepository(table)

            # Get today's date string
            from datetime import datetime
            today_str = datetime.utcnow().strftime('%Y%m%d')

            # Count hints and executions today
            hints_today = usage_repo.get_daily_usage_count_by_email(
                user.email,
                'hint',
                today_str
            )
            executions_today = usage_repo.get_daily_usage_count_by_email(
                user.email,
                'execution',
                today_str
            )

            # Count total unique problems
            total_problems = history_repo.count_unique_problems(user.email)

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

        # Cache the result for 60 seconds (shorter TTL for usage data)
        ttl = 60
        cache.set(cache_key, response_data, ttl)
        logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")

        return Response(response_data, status=status.HTTP_200_OK)
