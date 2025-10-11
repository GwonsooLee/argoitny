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

            # Serialize with latest plan information (ASYNC)
            serialized_user = await serialize_dynamodb_user(user_dict)

            return Response(serialized_user, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error fetching user profile: {e}')
            return Response(
                {'error': f'Failed to fetch user profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

            # Serialize and return updated user info (ASYNC)
            serialized_user = await serialize_dynamodb_user(updated_user)
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


class SubmitConsentsView(APIView):
    """Submit user consents for privacy, terms, and code ownership"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def post(self, request):
        """
        Submit user consents

        Request body:
            {
                "privacy_agreed": true,
                "terms_agreed": true,
                "code_ownership_agreed": true
            }

        Returns:
            {
                "message": "Consents saved successfully",
                "consents": {
                    "privacy_agreed_at": "2025-01-11T12:00:00Z",
                    "terms_agreed_at": "2025-01-11T12:00:00Z",
                    "code_ownership_agreed_at": "2025-01-11T12:00:00Z"
                }
            }
        """
        try:
            # Get user email from JWT token
            user_email = await sync_to_async(lambda: request.user.email)()

            # Get consent flags from request
            privacy_agreed = request.data.get('privacy_agreed', False)
            terms_agreed = request.data.get('terms_agreed', False)
            code_ownership_agreed = request.data.get('code_ownership_agreed', False)

            # Validate that all consents are True
            if not (privacy_agreed and terms_agreed and code_ownership_agreed):
                return Response(
                    {'error': 'All consents must be accepted to continue'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get current timestamp
            timestamp = int(timezone.now().timestamp())

            # Initialize async repository
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)
                user_repo = AsyncUserRepository(table)

                # Get user by email
                user_dict = await user_repo.get_user_by_email(user_email)
                if not user_dict:
                    return Response(
                        {'error': 'User not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Update consent timestamps
                await user_repo.update_user(
                    user_id=user_dict['user_id'],
                    updates={
                        'privacy_agreed_at': timestamp,
                        'terms_agreed_at': timestamp,
                        'code_ownership_agreed_at': timestamp
                    }
                )

                # Get updated user
                updated_user = await user_repo.get_user_by_email(user_email)

            # Format timestamps for response
            consent_timestamps = {
                'privacy_agreed_at': updated_user.get('privacy_agreed_at'),
                'terms_agreed_at': updated_user.get('terms_agreed_at'),
                'code_ownership_agreed_at': updated_user.get('code_ownership_agreed_at')
            }

            return Response(
                {
                    'message': 'Consents saved successfully',
                    'consents': consent_timestamps
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f'Error saving consents: {e}')
            return Response(
                {'error': f'Failed to save consents: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetConsentsView(APIView):
    """Get user's consent status"""
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    async def get(self, request):
        """
        Get user's consent status

        Returns:
            {
                "privacy_agreed_at": "2025-01-11T12:00:00Z" or null,
                "terms_agreed_at": "2025-01-11T12:00:00Z" or null,
                "code_ownership_agreed_at": "2025-01-11T12:00:00Z" or null,
                "all_consents_given": true/false
            }
        """
        try:
            # Get user email from JWT token
            user_email = await sync_to_async(lambda: request.user.email)()

            # Initialize async repository
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)
                user_repo = AsyncUserRepository(table)

                # Get user by email
                user_dict = await user_repo.get_user_by_email(user_email)
                if not user_dict:
                    return Response(
                        {'error': 'User not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Extract consent timestamps
            privacy_agreed_at = user_dict.get('privacy_agreed_at')
            terms_agreed_at = user_dict.get('terms_agreed_at')
            code_ownership_agreed_at = user_dict.get('code_ownership_agreed_at')

            # Check if all consents are given
            all_consents_given = all([
                privacy_agreed_at is not None,
                terms_agreed_at is not None,
                code_ownership_agreed_at is not None
            ])

            return Response(
                {
                    'privacy_agreed_at': privacy_agreed_at,
                    'terms_agreed_at': terms_agreed_at,
                    'code_ownership_agreed_at': code_ownership_agreed_at,
                    'all_consents_given': all_consents_given
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f'Error fetching consent status: {e}')
            return Response(
                {'error': f'Failed to fetch consent status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
