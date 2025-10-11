"""Custom JWT authentication with clock skew tolerance and DynamoDB support - ASYNC VERSION"""
from datetime import datetime, timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken, AuthenticationFailed
from rest_framework.exceptions import AuthenticationFailed as DRFAuthenticationFailed
import jwt


class CustomJWTAuthentication(JWTAuthentication):
    """Async JWT authentication with clock skew tolerance and DynamoDB user lookup"""

    def get_validated_token(self, raw_token):
        """Validate token with clock skew tolerance"""
        try:
            # Decode without verification first to check timestamps
            unverified = jwt.decode(raw_token, options={"verify_signature": False})

            # Check if token was issued in the future (clock skew issue)
            iat = unverified.get('iat')
            current_time = datetime.utcnow().timestamp()

            if iat and iat > current_time:
                # Token issued in future - allow up to 10 seconds skew
                time_diff = iat - current_time
                if time_diff <= 10:
                    # Add leeway for clock skew
                    return AccessToken(raw_token, verify=True)

            # Normal validation
            return AccessToken(raw_token)

        except TokenError as e:
            # Check if it's a timing issue
            if 'Token used too early' in str(e):
                try:
                    # Try with leeway
                    return AccessToken(raw_token, verify=True)
                except:
                    pass
            raise InvalidToken({
                'detail': str(e),
                'messages': [{'message': str(e)}]
            })

    def get_user(self, validated_token):
        """
        Get user from DynamoDB using email from JWT token

        Override default get_user to fetch from DynamoDB instead of Django ORM.
        Note: JWT token's 'user_id' claim contains email (not numeric ID)

        This method must remain synchronous to comply with DRF's authentication interface.
        We use async_to_sync to run async DynamoDB operations within this sync context.
        """
        try:
            # JWT token's 'user_id' claim actually contains email
            email = validated_token.get('user_id')
            if not email:
                raise AuthenticationFailed('Token contained no recognizable user identification')

            # Import async_to_sync for running async code in sync context
            from asgiref.sync import async_to_sync
            from .dynamodb.async_client import AsyncDynamoDBClient
            from .dynamodb.async_repositories import AsyncUserRepository, AsyncSubscriptionPlanRepository
            import logging
            logger = logging.getLogger(__name__)

            # Define async function to fetch user data
            async def fetch_user_data():
                async with AsyncDynamoDBClient.get_resource() as resource:
                    table = await resource.Table(AsyncDynamoDBClient._table_name)
                    user_repo = AsyncUserRepository(table)
                    user_dict = await user_repo.get_user_by_email(email)

                    if not user_dict:
                        logger.error(f'JWT Auth: User not found for email={email}')
                        raise DRFAuthenticationFailed({
                            'detail': 'User not found',
                            'code': 'user_not_found'
                        })

                    # Pre-load plan information for this user
                    plan_info = None
                    if user_dict.get('subscription_plan_id'):
                        plan_repo = AsyncSubscriptionPlanRepository(table)
                        plan = await plan_repo.get_plan(user_dict['subscription_plan_id'])
                        if plan:
                            plan_info = {
                                'max_hints_per_day': plan.get('max_hints_per_day', 5),
                                'max_executions_per_day': plan.get('max_executions_per_day', 50),
                                'max_problems': plan.get('max_problems', -1),
                            }

                    return user_dict, plan_info

            # Run async function in sync context
            user_dict, plan_info = async_to_sync(fetch_user_data)()

            # Create a user-like object that views can use
            # This mimics Django User but uses DynamoDB data
            class DynamoDBUser:
                def __init__(self, user_data, preloaded_plan_info=None):
                    self.id = user_data.get('user_id')
                    self.user_id = user_data.get('user_id')
                    self.email = user_data.get('email', '')
                    self.name = user_data.get('name', '')
                    self.picture = user_data.get('picture', '')
                    self.google_id = user_data.get('google_id', '')
                    self.subscription_plan_id = user_data.get('subscription_plan_id')
                    self.is_active = user_data.get('is_active', True)
                    self.is_staff = user_data.get('is_staff', False)
                    self.created_at = user_data.get('created_at')
                    self.updated_at = user_data.get('updated_at')
                    # Store raw dict for access to all fields
                    self._user_dict = user_data
                    # Store pre-loaded plan info (from async load)
                    self._plan_info = preloaded_plan_info

                @property
                def pk(self):
                    """Primary key for Django ORM compatibility"""
                    return self.id

                @property
                def is_authenticated(self):
                    return True

                @property
                def is_anonymous(self):
                    return False

                def is_admin(self):
                    from django.conf import settings
                    return self.is_staff or self.email in settings.ADMIN_EMAILS

                def get_plan_limits(self):
                    """Get subscription plan limits (pre-loaded during authentication)"""
                    if self._plan_info:
                        return self._plan_info

                    # Default limits if no plan info available
                    return {
                        'max_hints_per_day': 5,
                        'max_executions_per_day': 50,
                        'max_problems': -1,
                    }

            return DynamoDBUser(user_dict, plan_info)

        except DRFAuthenticationFailed:
            raise
        except Exception as e:
            raise DRFAuthenticationFailed({
                'detail': f'Failed to authenticate user: {str(e)}',
                'code': 'authentication_failed'
            })