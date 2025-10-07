"""Google OAuth Service"""
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from ..models import User, SubscriptionPlan


class GoogleOAuthService:
    """Handle Google OAuth authentication"""

    @staticmethod
    def verify_token(token):
        """
        Verify Google ID token and return user info

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
    def get_or_create_user(google_user_info, plan_name=None):
        """
        Get or create user from Google user info

        Args:
            google_user_info: Dict containing Google user information
            plan_name: Optional subscription plan name (defaults to 'Free')

        Returns:
            tuple: (User instance, created boolean)
        """
        # Determine if user is admin
        is_admin_user = google_user_info['email'] in settings.ADMIN_EMAILS

        # Get subscription plan
        if is_admin_user:
            # Admin users get Admin plan automatically
            plan = SubscriptionPlan.objects.filter(name='Admin', is_active=True).first()
        elif plan_name:
            # Use provided plan name (must be active and not Admin)
            plan = SubscriptionPlan.objects.filter(name=plan_name, is_active=True).exclude(name='Admin').first()
        else:
            # Default to Free plan
            plan = SubscriptionPlan.objects.filter(name='Free', is_active=True).first()

        user, created = User.objects.get_or_create(
            google_id=google_user_info['google_id'],
            defaults={
                'email': google_user_info['email'],
                'name': google_user_info['name'],
                'picture': google_user_info['picture'],
                'subscription_plan': plan,
            }
        )

        # Update user info if not created
        if not created:
            user.name = google_user_info['name']
            user.picture = google_user_info['picture']

            # Update to Admin plan if user became admin
            if is_admin_user and user.subscription_plan and user.subscription_plan.name != 'Admin':
                admin_plan = SubscriptionPlan.objects.filter(name='Admin', is_active=True).first()
                if admin_plan:
                    user.subscription_plan = admin_plan

            # If existing user with no plan, assign Free plan (or provided plan for first-time selection)
            if not user.subscription_plan:
                user.subscription_plan = plan

            user.save()

        return user, created
