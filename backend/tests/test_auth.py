"""Tests for authentication views - Async Version"""
import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from asgiref.sync import sync_to_async
from api.models import User


@pytest.mark.django_db
@pytest.mark.asyncio
class TestGoogleLogin:
    """Test Google OAuth login endpoint"""

    async def test_login_success_new_user(self, api_client):
        """Test successful login with new user creation (async)"""
        with patch('api.services.google_oauth.GoogleOAuthService.verify_token') as mock_verify, \
             patch('api.services.google_oauth.GoogleOAuthService.get_or_create_user') as mock_get_user:

            # Mock Google verification
            mock_verify.return_value = {
                'sub': 'google123',
                'email': 'newuser@example.com',
                'name': 'New User',
                'picture': 'https://example.com/pic.jpg'
            }

            # Mock user creation - async
            user = await sync_to_async(User.objects.create_user)(
                email='newuser@example.com',
                name='New User',
                picture='https://example.com/pic.jpg',
                google_id='google123'
            )
            mock_get_user.return_value = user

            response = await sync_to_async(api_client.post)('/api/auth/google/', {
                'token': 'valid_google_token'
            })

            assert response.status_code == status.HTTP_200_OK
            assert 'user' in response.data
            assert 'access' in response.data
            assert 'refresh' in response.data
            assert response.data['user']['email'] == 'newuser@example.com'

    async def test_login_success_existing_user(self, api_client, sample_user):
        """Test successful login with existing user (async)"""
        with patch('api.services.google_oauth.GoogleOAuthService.verify_token') as mock_verify, \
             patch('api.services.google_oauth.GoogleOAuthService.get_or_create_user') as mock_get_user:

            mock_verify.return_value = {
                'sub': 'google123',
                'email': sample_user.email,
                'name': sample_user.name,
                'picture': sample_user.picture
            }
            mock_get_user.return_value = sample_user

            response = await sync_to_async(api_client.post)('/api/auth/google/', {
                'token': 'valid_google_token'
            })

            assert response.status_code == status.HTTP_200_OK
            assert response.data['user']['email'] == sample_user.email

    async def test_login_missing_token(self, api_client):
        """Test login without token (async)"""
        response = await sync_to_async(api_client.post)('/api/auth/google/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'required' in response.data['error'].lower()

    async def test_login_invalid_token(self, api_client):
        """Test login with invalid Google token (async)"""
        with patch('api.services.google_oauth.GoogleOAuthService.verify_token') as mock_verify:
            mock_verify.side_effect = ValueError('Invalid token')

            response = await sync_to_async(api_client.post)('/api/auth/google/', {
                'token': 'invalid_token'
            })

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert 'error' in response.data

    async def test_login_google_service_error(self, api_client):
        """Test login when Google service fails (async)"""
        with patch('api.services.google_oauth.GoogleOAuthService.verify_token') as mock_verify:
            mock_verify.side_effect = Exception('Google API error')

            response = await sync_to_async(api_client.post)('/api/auth/google/', {
                'token': 'valid_token'
            })

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert 'error' in response.data


@pytest.mark.django_db
class TestTokenRefresh:
    """Test JWT token refresh endpoint"""

    def test_refresh_success(self, api_client, jwt_tokens):
        """Test successful token refresh"""
        response = api_client.post('/api/auth/refresh/', {
            'refresh': jwt_tokens['refresh']
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_missing_token(self, api_client):
        """Test refresh without token"""
        response = api_client.post('/api/auth/refresh/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_refresh_invalid_token(self, api_client):
        """Test refresh with invalid token"""
        response = api_client.post('/api/auth/refresh/', {
            'refresh': 'invalid_refresh_token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'error' in response.data

    def test_refresh_expired_token(self, api_client):
        """Test refresh with expired token"""
        expired_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTYwMDAwMDAwMH0.fake'

        response = api_client.post('/api/auth/refresh/', {
            'refresh': expired_token
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:
    """Test logout endpoint"""

    def test_logout_success(self, authenticated_client, jwt_tokens):
        """Test successful logout"""
        with patch('api.views.auth.RefreshToken') as MockRefreshToken:
            mock_token = Mock()
            mock_token.blacklist = Mock()
            MockRefreshToken.return_value = mock_token

            response = authenticated_client.post('/api/auth/logout/', {
                'refresh': jwt_tokens['refresh']
            })

            assert response.status_code == status.HTTP_200_OK
            assert 'message' in response.data
            assert 'success' in response.data['message'].lower()
            mock_token.blacklist.assert_called_once()

    def test_logout_missing_token(self, authenticated_client):
        """Test logout without refresh token"""
        response = authenticated_client.post('/api/auth/logout/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_logout_invalid_token(self, authenticated_client):
        """Test logout with invalid token"""
        response = authenticated_client.post('/api/auth/logout/', {
            'refresh': 'invalid_token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication"""
        response = api_client.post('/api/auth/logout/', {
            'refresh': 'some_token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthenticationIntegration:
    """Integration tests for authentication flow"""

    def test_full_auth_flow(self, api_client):
        """Test complete authentication flow: login -> refresh -> logout"""
        # Step 1: Login
        with patch('api.services.google_oauth.GoogleOAuthService.verify_token') as mock_verify, \
             patch('api.services.google_oauth.GoogleOAuthService.get_or_create_user') as mock_get_user:

            mock_verify.return_value = {
                'sub': 'google789',
                'email': 'flow@example.com',
                'name': 'Flow User',
                'picture': 'https://example.com/flow.jpg'
            }

            user = User.objects.create_user(
                email='flow@example.com',
                name='Flow User',
                picture='https://example.com/flow.jpg',
                google_id='google789'
            )
            mock_get_user.return_value = user

            login_response = api_client.post('/api/auth/google/', {
                'token': 'google_token'
            })

            assert login_response.status_code == status.HTTP_200_OK
            access_token = login_response.data['access']
            refresh_token = login_response.data['refresh']

            # Step 2: Use access token for authenticated request
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            account_response = api_client.get('/api/account/stats/')
            assert account_response.status_code == status.HTTP_200_OK

            # Step 3: Refresh token
            refresh_response = api_client.post('/api/auth/refresh/', {
                'refresh': refresh_token
            })
            assert refresh_response.status_code == status.HTTP_200_OK
            new_access_token = refresh_response.data['access']

            # Step 4: Use new access token
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
            account_response2 = api_client.get('/api/account/stats/')
            assert account_response2.status_code == status.HTTP_200_OK

            # Step 5: Logout
            with patch('api.views.auth.RefreshToken') as MockRefreshToken:
                mock_token = Mock()
                mock_token.blacklist = Mock()
                MockRefreshToken.return_value = mock_token

                logout_response = api_client.post('/api/auth/logout/', {
                    'refresh': refresh_token
                })
                assert logout_response.status_code == status.HTTP_200_OK
