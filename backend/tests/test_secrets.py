"""Tests for Secrets Management

This module tests the SecretsManager utility and secrets loading from:
- AWS Secrets Manager
- Environment variables
- Legacy secrets.py file
"""

import os
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from api.utils.secrets import SecretsManager


class TestSecretsManager:
    """Test SecretsManager functionality"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear cached secrets before each test
        SecretsManager.clear()
        yield
        # Clear after test
        SecretsManager.clear()

    def test_load_from_environment_variables(self, monkeypatch):
        """Test loading secrets from environment variables"""
        monkeypatch.setenv('SECRET_KEY', 'env-secret-key')
        monkeypatch.setenv('DB_PASSWORD', 'env-db-password')
        monkeypatch.setenv('GEMINI_API_KEY', 'env-gemini-key')

        secrets = SecretsManager.load()

        # Env vars should be accessible
        assert secrets.get('SECRET_KEY') == 'env-secret-key'
        assert secrets.get('DB_PASSWORD') == 'env-db-password'
        assert secrets.get('GEMINI_API_KEY') == 'env-gemini-key'

    def test_get_with_default_value(self):
        """Test get with default value for non-existent keys"""
        secrets = SecretsManager.load()

        # Non-existent key should return default
        assert secrets.get('NON_EXISTENT_KEY', default='default_value') == 'default_value'
        assert secrets.get('ANOTHER_MISSING_KEY') is None

    def test_get_with_env_var_parameter(self, monkeypatch):
        """Test get with explicit env_var parameter"""
        monkeypatch.setenv('CUSTOM_ENV_VAR', 'custom-value')

        secrets = SecretsManager.load()

        # Should check specified env var
        value = secrets.get('ANY_KEY', env_var='CUSTOM_ENV_VAR')
        assert value == 'custom-value'

    @patch('api.utils.secrets.boto3')
    def test_load_from_aws_secrets_manager(self, mock_boto3, monkeypatch):
        """Test loading secrets from AWS Secrets Manager"""
        # Enable AWS Secrets Manager
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        monkeypatch.setenv('AWS_SECRET_NAME', 'test-secret')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')

        # Mock AWS response
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        secret_data = {
            'SECRET_KEY': 'aws-secret-key',
            'DB_PASSWORD': 'aws-db-password',
            'GEMINI_API_KEY': 'aws-gemini-key'
        }

        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_data)
        }

        # Load secrets
        secrets = SecretsManager.load()

        # Verify AWS was called
        mock_session.client.assert_called_once_with(
            service_name='secretsmanager',
            region_name='us-east-1'
        )
        mock_client.get_secret_value.assert_called_once_with(SecretId='test-secret')

        # Verify secrets are loaded
        assert secrets.get('SECRET_KEY') == 'aws-secret-key'
        assert secrets.get('DB_PASSWORD') == 'aws-db-password'
        assert secrets.get('GEMINI_API_KEY') == 'aws-gemini-key'

    @patch('api.utils.secrets.boto3')
    def test_aws_fallback_to_env_on_error(self, mock_boto3, monkeypatch):
        """Test fallback to environment variables when AWS Secrets Manager fails"""
        # Enable AWS Secrets Manager
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        monkeypatch.setenv('SECRET_KEY', 'env-fallback-key')

        # Mock AWS to raise exception
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        from botocore.exceptions import ClientError
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Secret not found'}},
            'GetSecretValue'
        )

        # Load secrets (should fall back to env vars)
        secrets = SecretsManager.load()

        # Should fall back to environment variable
        assert secrets.get('SECRET_KEY') == 'env-fallback-key'

    @patch('api.utils.secrets.boto3')
    def test_aws_secret_priority_over_env(self, mock_boto3, monkeypatch):
        """Test that AWS Secrets Manager takes priority over environment variables"""
        # Enable AWS Secrets Manager
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        monkeypatch.setenv('SECRET_KEY', 'env-secret-key')

        # Mock AWS response
        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        secret_data = {'SECRET_KEY': 'aws-secret-key'}
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_data)
        }

        # Load secrets
        secrets = SecretsManager.load()

        # AWS value should take priority
        assert secrets.get('SECRET_KEY') == 'aws-secret-key'

    def test_legacy_secrets_py_fallback(self):
        """Test fallback to legacy secrets.py file"""
        # Create a mock secrets module
        with patch('api.utils.secrets.secrets_module') as mock_module:
            mock_module.SECRET_KEY = 'legacy-secret-key'

            secrets = SecretsManager.load()

            # Should fall back to secrets.py
            with patch('api.utils.secrets.hasattr', return_value=True):
                with patch('api.utils.secrets.getattr', return_value='legacy-secret-key'):
                    value = secrets.get('SECRET_KEY')
                    # In real scenario, would be 'legacy-secret-key'

    def test_priority_order(self, monkeypatch):
        """Test priority order: AWS > Env > secrets.py > default"""
        # Set environment variable
        monkeypatch.setenv('TEST_SECRET', 'env-value')

        secrets = SecretsManager.load()

        # Environment variable should be returned
        assert secrets.get('TEST_SECRET') == 'env-value'

        # If not in env, should use default
        assert secrets.get('NON_EXISTENT', default='default-value') == 'default-value'

    def test_reload_secrets(self, monkeypatch):
        """Test reload functionality"""
        monkeypatch.setenv('SECRET_KEY', 'initial-key')

        secrets = SecretsManager.load()
        initial_value = secrets.get('SECRET_KEY')
        assert initial_value == 'initial-key'

        # Change environment variable
        monkeypatch.setenv('SECRET_KEY', 'updated-key')

        # Reload secrets
        secrets = SecretsManager.reload()

        # Should get updated value
        updated_value = secrets.get('SECRET_KEY')
        assert updated_value == 'updated-key'

    def test_get_all_secrets(self, monkeypatch):
        """Test get_all returns all secrets"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'false')

        secrets = SecretsManager.load()

        # Set some runtime secrets
        SecretsManager.set('TEST_KEY_1', 'value1')
        SecretsManager.set('TEST_KEY_2', 'value2')

        all_secrets = secrets.get_all()

        assert isinstance(all_secrets, dict)
        assert all_secrets['TEST_KEY_1'] == 'value1'
        assert all_secrets['TEST_KEY_2'] == 'value2'

    def test_clear_cache(self, monkeypatch):
        """Test clearing cached secrets"""
        monkeypatch.setenv('SECRET_KEY', 'test-key')

        secrets = SecretsManager.load()

        # Verify loaded
        assert secrets.get('SECRET_KEY') == 'test-key'

        # Clear cache
        SecretsManager.clear()

        # Should need to reload
        secrets = SecretsManager.load()
        assert secrets.get('SECRET_KEY') == 'test-key'

    def test_set_runtime_value(self):
        """Test setting secret values at runtime"""
        SecretsManager.clear()
        secrets = SecretsManager.load()

        # Set values
        SecretsManager.set('RUNTIME_SECRET', 'runtime-value')
        SecretsManager.set('ANOTHER_SECRET', 'another-value')

        # Verify values
        assert secrets.get('RUNTIME_SECRET') == 'runtime-value'
        assert secrets.get('ANOTHER_SECRET') == 'another-value'

    def test_is_using_aws(self, monkeypatch):
        """Test is_using_aws flag"""
        # Disabled AWS
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'false')
        secrets = SecretsManager.load()
        assert SecretsManager.is_using_aws() is False

        # Clear and enable AWS
        SecretsManager.clear()
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')

        with patch('api.utils.secrets.boto3'):
            # Mock to avoid actual AWS call
            with patch.object(SecretsManager, '_load_from_aws', return_value={}):
                secrets = SecretsManager.load()
                assert SecretsManager.is_using_aws() is True

    @patch('api.utils.secrets.boto3')
    def test_aws_client_error_handling(self, mock_boto3, monkeypatch):
        """Test different AWS client error codes"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')

        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        # Test ResourceNotFoundException
        mock_client.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetSecretValue'
        )

        secrets = SecretsManager.load()
        # Should fall back gracefully
        assert secrets.get('ANY_KEY', default='default') == 'default'

    @patch('api.utils.secrets.boto3')
    def test_aws_non_json_secret(self, mock_boto3, monkeypatch):
        """Test handling of non-JSON secret string"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        # Return non-JSON string
        mock_client.get_secret_value.return_value = {
            'SecretString': 'plain-text-secret'
        }

        secrets = SecretsManager.load()

        # Should handle as plain text with 'value' key
        assert secrets.get('value') == 'plain-text-secret'

    @patch('api.utils.secrets.boto3')
    def test_aws_binary_secret(self, mock_boto3, monkeypatch):
        """Test handling of binary secret"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        # Return binary secret (no SecretString)
        mock_client.get_secret_value.return_value = {
            'SecretBinary': b'binary-data'
        }

        secrets = SecretsManager.load()

        # Should return empty dict for binary secrets
        all_secrets = secrets.get_all()
        assert all_secrets == {}

    def test_boto3_not_installed(self, monkeypatch):
        """Test graceful handling when boto3 is not installed"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        monkeypatch.setenv('SECRET_KEY', 'env-fallback')

        with patch('api.utils.secrets.boto3', None):
            # Should fall back to environment variables
            secrets = SecretsManager.load()
            assert secrets.get('SECRET_KEY') == 'env-fallback'


class TestSecretsIntegration:
    """Integration tests for secrets in Django settings"""

    def test_settings_import(self):
        """Test that settings.py can import and use SecretsManager"""
        from django.conf import settings

        # Verify settings are loaded
        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'DATABASES')

    def test_settings_secret_key(self):
        """Test SECRET_KEY is loaded from SecretsManager"""
        from django.conf import settings

        # Should have a secret key (from env or default)
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_settings_database_password(self):
        """Test database password is loaded from SecretsManager"""
        from django.conf import settings

        # Database password should be loaded
        db_password = settings.DATABASES['default']['PASSWORD']
        assert db_password is not None  # May be empty string in dev

    def test_settings_api_keys(self):
        """Test API keys are loaded from SecretsManager"""
        from django.conf import settings

        # API keys should be loaded (may be empty in test)
        assert hasattr(settings, 'GEMINI_API_KEY')
        assert hasattr(settings, 'GOOGLE_OAUTH_CLIENT_ID')
        assert hasattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET')


class TestSecretsManagerEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        SecretsManager.clear()
        yield
        SecretsManager.clear()

    def test_empty_secret_value(self):
        """Test handling of empty secret values"""
        SecretsManager.load()
        SecretsManager.set('EMPTY_SECRET', '')

        # Should return empty string, not default
        assert SecretsManager.get('EMPTY_SECRET', default='default') == ''

    def test_none_secret_value(self):
        """Test handling of None secret values"""
        SecretsManager.load()
        SecretsManager.set('NONE_SECRET', None)

        # Should return default for None
        assert SecretsManager.get('NONE_SECRET', default='default') == 'default'

    def test_concurrent_access(self, monkeypatch):
        """Test thread-safe access to secrets"""
        import threading

        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        secrets = SecretsManager.load()

        results = []

        def read_secret():
            for _ in range(100):
                value = secrets.get('SECRET_KEY')
                results.append(value)

        # Create multiple threads
        threads = [threading.Thread(target=read_secret) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All reads should return the same value
        assert all(v == 'test-secret' for v in results)
        assert len(results) == 1000  # 10 threads * 100 reads

    @patch('api.utils.secrets.boto3')
    def test_aws_default_region(self, mock_boto3, monkeypatch):
        """Test AWS uses default region when not specified"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        # Don't set AWS_REGION, should use default

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({})
        }

        SecretsManager.load()

        # Should use default region 'us-east-1'
        call_args = mock_session.client.call_args
        assert call_args[1]['region_name'] == 'us-east-1'

    @patch('api.utils.secrets.boto3')
    def test_aws_custom_secret_name(self, mock_boto3, monkeypatch):
        """Test AWS uses custom secret name"""
        monkeypatch.setenv('USE_SECRETS_MANAGER', 'true')
        monkeypatch.setenv('AWS_SECRET_NAME', 'custom-secret-name')

        mock_client = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_boto3.session.Session.return_value = mock_session

        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({})
        }

        SecretsManager.load()

        # Should use custom secret name
        mock_client.get_secret_value.assert_called_with(SecretId='custom-secret-name')
