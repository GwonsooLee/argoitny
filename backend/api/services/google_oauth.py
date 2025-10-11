"""Google OAuth Service - ASYNC VERSION"""
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from asgiref.sync import sync_to_async


class GoogleOAuthService:
    """Handle Google OAuth authentication with async support"""

    @staticmethod
    def verify_token(token):
        """
        Verify Google ID token and return user info

        Note: This method remains synchronous because Google's library is sync-only.
        It's fast enough that async conversion isn't necessary.

        Args:
            token: Google ID token

        Returns:
            dict: User information from Google

        Raises:
            ValueError: If token is invalid
        """
        try:
            # Verify token with clock skew tolerance of 60 seconds
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID,
                clock_skew_in_seconds=60
            )

            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
            }
        except ValueError as e:
            raise ValueError(f'Invalid token: {str(e)}')

    @staticmethod
    async def get_or_create_user(google_user_info, plan_name=None):
        """
        Get or create user from Google user info using DynamoDB (ASYNC)

        Args:
            google_user_info: Dict containing Google user information
            plan_name: Optional subscription plan name (defaults to 'Free')

        Returns:
            tuple: (User dict, created boolean)
        """
        from ..dynamodb.async_client import AsyncDynamoDBClient
        from ..dynamodb.async_repositories import AsyncUserRepository, AsyncSubscriptionPlanRepository

        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table(AsyncDynamoDBClient._table_name)
            user_repo = AsyncUserRepository(table)
            plan_repo = AsyncSubscriptionPlanRepository(table)

            # Check if user exists by Google ID
            existing_user = await user_repo.get_user_by_google_id(google_user_info['google_id'])

            # Determine if user is admin
            is_admin_user = google_user_info['email'] in settings.ADMIN_EMAILS

            # Get all plans and find the right one
            all_plans = await plan_repo.list_plans()

            plan_id = None

            if is_admin_user:
                # Admin users get Admin plan automatically
                admin_plan = next((p for p in all_plans if p['name'] == 'Admin' and p.get('is_active', True)), None)
                plan_id = admin_plan['id'] if admin_plan else 3
            elif plan_name:
                # Use provided plan name (must be active and not Admin)
                custom_plan = next((p for p in all_plans if p['name'] == plan_name and p.get('is_active', True) and p['name'] != 'Admin'), None)
                plan_id = custom_plan['id'] if custom_plan else None
            else:
                # Default to Free plan for new users
                free_plan = next((p for p in all_plans if p['name'] == 'Free' and p.get('is_active', True)), None)
                plan_id = free_plan['id'] if free_plan else 1

            if existing_user:
                # User exists - update their info
                async with AsyncDynamoDBClient.get_resource() as resource:
                    table = await resource.Table(AsyncDynamoDBClient._table_name)
                    user_repo = AsyncUserRepository(table)

                    updates = {
                        'name': google_user_info['name'],
                        'picture': google_user_info['picture'],
                    }

                    # Update to Admin plan if user became admin
                    if is_admin_user and existing_user.get('subscription_plan_id') != plan_id:
                        updates['subscription_plan_id'] = plan_id

                    # If existing user with no plan, assign Free plan (or provided plan)
                    if not existing_user.get('subscription_plan_id'):
                        updates['subscription_plan_id'] = plan_id

                    await user_repo.update_user(existing_user['user_id'], updates)

                    # Get updated user
                    updated_user = await user_repo.get_user_by_id(existing_user['user_id'])
                    return updated_user, False

            else:
                # Create new user
                # Generate new user ID (in production, use a proper ID generation strategy)
                # For now, we'll use a timestamp-based approach
                import time
                new_user_id = int(time.time() * 1000000) % 2147483647  # Max int32

                async with AsyncDynamoDBClient.get_resource() as resource:
                    table = await resource.Table(AsyncDynamoDBClient._table_name)
                    user_repo = AsyncUserRepository(table)

                    # Check if user exists by email (edge case: user with email but no google_id)
                    email_user = await user_repo.get_user_by_email(google_user_info['email'])
                    if email_user:
                        # Update existing user with Google ID
                        updates = {
                            'google_id': google_user_info['google_id'],
                            'name': google_user_info['name'],
                            'picture': google_user_info['picture'],
                        }
                        # Assign plan if user doesn't have one (defaults to Free)
                        if not email_user.get('subscription_plan_id'):
                            updates['subscription_plan_id'] = plan_id
                        await user_repo.update_user(email_user['user_id'], updates)

                        # Get updated user
                        updated_user = await user_repo.get_user_by_id(email_user['user_id'])
                        return updated_user, False

                    # Create completely new user
                    user_data = {
                        'user_id': new_user_id,
                        'email': google_user_info['email'],
                        'name': google_user_info['name'],
                        'picture': google_user_info['picture'],
                        'google_id': google_user_info['google_id'],
                        'is_active': True,
                        'is_staff': is_admin_user,
                        'subscription_plan_id': plan_id,  # Assign plan by default
                    }

                    new_user = await user_repo.create_user(user_data)
                    return new_user, True
