"""Google OAuth Service"""
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from ..models import User


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
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID
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
    def get_or_create_user(google_user_info):
        """
        Get or create user from Google user info

        Args:
            google_user_info: Dict containing Google user information

        Returns:
            User: User instance
        """
        user, created = User.objects.get_or_create(
            google_id=google_user_info['google_id'],
            defaults={
                'email': google_user_info['email'],
                'name': google_user_info['name'],
                'picture': google_user_info['picture'],
            }
        )

        # Update user info if not created
        if not created:
            user.name = google_user_info['name']
            user.picture = google_user_info['picture']
            user.save()

        return user
