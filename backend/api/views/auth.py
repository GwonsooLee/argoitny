"""
Authentication Views

This module handles user authentication using Google OAuth and JWT tokens.
User data is stored in DynamoDB via UserRepository, accessed through GoogleOAuthService.
SubscriptionPlan configuration data remains in PostgreSQL via Django ORM.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from ..services.google_oauth import GoogleOAuthService
from ..serializers import SubscriptionPlanSerializer
# from ..models import SubscriptionPlan  # REMOVED - using DynamoDB SubscriptionPlanRepository
from ..utils.jwt_helper import generate_tokens_for_user
from ..utils.serializer_helper import serialize_dynamodb_user


class GoogleLoginView(APIView):
    """
    Google OAuth login endpoint

    Uses DynamoDB UserRepository (via GoogleOAuthService) for user data storage.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Login with Google ID token

        Request body:
            {
                "token": "google_id_token",
                "plan": "Free"  # Optional: "Free" (default), "Pro", "Pro+"
            }

        Returns:
            {
                "user": {...},  # User dict from DynamoDB
                "access": "jwt_access_token",
                "refresh": "jwt_refresh_token",
                "is_new_user": true/false
            }

        User data flow:
            1. Verify Google token
            2. Get or create user in DynamoDB (via GoogleOAuthService.get_or_create_user)
            3. Returns user dict with fields: user_id, email, name, picture,
               google_id, subscription_plan_id, is_active, is_staff
            4. Generate JWT tokens from user dict
            5. Return serialized user data and tokens
        """
        token = request.data.get('token')
        plan_name = request.data.get('plan', 'Free')

        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify Google token and get user info
            google_user_info = GoogleOAuthService.verify_token(token)

            # Get or create user in DynamoDB (returns dict)
            # GoogleOAuthService internally uses UserRepository for DynamoDB operations
            # Returns: (user_dict, created_boolean)
            user_dict, created = GoogleOAuthService.get_or_create_user(google_user_info, plan_name)

            # Generate JWT tokens from user dict
            # JWT helper works with user dicts (not Django User objects)
            tokens = generate_tokens_for_user(user_dict)

            # Serialize user data to match expected frontend format
            # Converts DynamoDB user dict to API response format
            serialized_user = serialize_dynamodb_user(user_dict)

            return Response({
                'user': serialized_user,
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'is_new_user': created,
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
    """
    JWT token refresh endpoint

    Token operations are stateless - user data from DynamoDB is not required.
    """
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
    """
    Logout endpoint

    Blacklists JWT refresh token. No DynamoDB operations required.
    """
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


class AvailablePlansView(APIView):
    """
    Get available subscription plans (excluding Admin plan)

    SubscriptionPlan data is now stored in DynamoDB.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get list of available subscription plans from DynamoDB

        Returns:
            [
                {
                    "id": 1,
                    "name": "Free",
                    "description": "Free plan with basic features",
                    "max_hints_per_day": 5,
                    "max_executions_per_day": 50,
                    "max_problems": -1,
                    "can_view_all_problems": true,
                    "can_register_problems": false,
                    "is_active": true
                },
                ...
            ]
        """
        try:
            from ..dynamodb.client import DynamoDBClient
            from ..dynamodb.repositories import SubscriptionPlanRepository

            table = DynamoDBClient.get_table()
            plan_repo = SubscriptionPlanRepository(table)

            # Get all plans from DynamoDB
            all_plans = plan_repo.list_plans()

            # Filter: only active plans, exclude Admin plan
            plans = [
                plan for plan in all_plans
                if plan.get('is_active', True) and plan.get('name') != 'Admin'
            ]

            # Sort by name
            plans.sort(key=lambda p: p.get('name', ''))

            return Response(plans, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch plans: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
