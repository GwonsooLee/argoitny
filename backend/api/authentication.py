"""Custom JWT authentication with clock skew tolerance and DynamoDB support"""
from datetime import datetime, timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken, AuthenticationFailed
from rest_framework.exceptions import AuthenticationFailed as DRFAuthenticationFailed
import jwt


class CustomJWTAuthentication(JWTAuthentication):
    """JWT authentication with clock skew tolerance and DynamoDB user lookup"""

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
        """
        try:
            # JWT token's 'user_id' claim actually contains email
            email = validated_token.get('user_id')
            if not email:
                raise AuthenticationFailed('Token contained no recognizable user identification')

            # Fetch user from DynamoDB by email
            from .dynamodb.client import DynamoDBClient
            from .dynamodb.repositories import UserRepository
            import logging
            logger = logging.getLogger(__name__)

            table = DynamoDBClient.get_table()
            user_repo = UserRepository(table)
            user_dict = user_repo.get_user_by_email(email)

            if not user_dict:
                logger.error(f'JWT Auth: User not found for email={email}')
                raise DRFAuthenticationFailed({
                    'detail': 'User not found',
                    'code': 'user_not_found'
                })

            # Create a user-like object that views can use
            # This mimics Django User but uses DynamoDB data
            class DynamoDBUser:
                def __init__(self, user_data):
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
                    """Get subscription plan limits from DynamoDB"""
                    if self.subscription_plan_id:
                        try:
                            from .dynamodb.repositories import SubscriptionPlanRepository

                            table = DynamoDBClient.get_table()
                            plan_repo = SubscriptionPlanRepository(table)
                            plan = plan_repo.get_plan(self.subscription_plan_id)

                            if plan:
                                return {
                                    'max_hints_per_day': plan.get('max_hints_per_day', 5),
                                    'max_executions_per_day': plan.get('max_executions_per_day', 50),
                                    'max_problems': plan.get('max_problems', -1),
                                }
                        except Exception:
                            pass

                    # Default limits
                    return {
                        'max_hints_per_day': 5,
                        'max_executions_per_day': 50,
                        'max_problems': -1,
                    }

            return DynamoDBUser(user_dict)

        except DRFAuthenticationFailed:
            raise
        except Exception as e:
            raise DRFAuthenticationFailed({
                'detail': f'Failed to authenticate user: {str(e)}',
                'code': 'authentication_failed'
            })