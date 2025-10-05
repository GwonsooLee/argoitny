"""Authentication Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from ..services.google_oauth import GoogleOAuthService
from ..serializers import UserSerializer


class GoogleLoginView(APIView):
    """Google OAuth login endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Login with Google ID token

        Request body:
            {
                "token": "google_id_token"
            }

        Returns:
            {
                "user": {...},
                "access": "jwt_access_token",
                "refresh": "jwt_refresh_token"
            }
        """
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify Google token and get user info
            google_user_info = GoogleOAuthService.verify_token(token)

            # Get or create user
            user = GoogleOAuthService.get_or_create_user(google_user_info)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': f'Login failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TokenRefreshView(APIView):
    """JWT token refresh endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Refresh JWT access token

        Request body:
            {
                "refresh": "jwt_refresh_token"
            }

        Returns:
            {
                "access": "new_jwt_access_token",
                "refresh": "new_jwt_refresh_token"  # if rotation enabled
            }
        """
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)

            # Get new access token
            response_data = {
                'access': str(refresh.access_token),
            }

            # If token rotation is enabled, return new refresh token
            if hasattr(refresh, 'refresh_token'):
                response_data['refresh'] = str(refresh)

            return Response(response_data, status=status.HTTP_200_OK)

        except TokenError as e:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': f'Token refresh failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """Logout endpoint"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Logout by blacklisting refresh token

        Request body:
            {
                "refresh": "jwt_refresh_token"
            }

        Returns:
            {
                "message": "Logged out successfully"
            }
        """
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )

        except TokenError:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {'error': f'Logout failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
