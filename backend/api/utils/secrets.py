"""Secrets Management Utility

This module handles loading secrets from AWS Secrets Manager with fallback to environment variables.

Usage:
    from api.utils.secrets import SecretsManager

    secrets = SecretsManager.load()
    secret_key = secrets.get('SECRET_KEY')
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages secrets from AWS Secrets Manager with environment variable fallback"""

    _secrets_cache: Optional[Dict[str, Any]] = None
    _use_aws: bool = False

    @classmethod
    def load(cls, secret_name: Optional[str] = None, region_name: Optional[str] = None, reload: bool = False) -> 'SecretsManager':
        """
        Load secrets from AWS Secrets Manager or environment variables

        Priority:
        1. AWS Secrets Manager (if USE_SECRETS_MANAGER=true)
        2. Environment variables
        3. Legacy secrets.py file (for backward compatibility)

        Args:
            secret_name: Name of the secret in AWS Secrets Manager (default: from env var)
            region_name: AWS region (default: from env var or 'us-east-1')
            reload: Force reload even if cached

        Returns:
            SecretsManager instance
        """
        if cls._secrets_cache is not None and not reload:
            return cls()

        # Check if AWS Secrets Manager should be used
        use_aws = os.getenv('USE_SECRETS_MANAGER', 'false').lower() == 'true'
        cls._use_aws = use_aws

        if use_aws:
            # Try to load from AWS Secrets Manager
            secret_name = secret_name or os.getenv('AWS_SECRET_NAME', 'algoitny-secrets')
            region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')

            try:
                cls._secrets_cache = cls._load_from_aws(secret_name, region_name)
                logger.info(f"Successfully loaded secrets from AWS Secrets Manager: {secret_name}")
            except Exception as e:
                logger.warning(f"Failed to load from AWS Secrets Manager: {e}. Falling back to environment variables.")
                cls._secrets_cache = {}
        else:
            logger.info("AWS Secrets Manager disabled. Using environment variables for secrets.")
            cls._secrets_cache = {}

        return cls()

    @staticmethod
    def _load_from_aws(secret_name: str, region_name: str) -> Dict[str, Any]:
        """
        Load secrets from AWS Secrets Manager

        Args:
            secret_name: Name of the secret
            region_name: AWS region

        Returns:
            Dictionary of secrets

        Raises:
            Exception: If AWS Secrets Manager is not available or secret not found
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("boto3 is required for AWS Secrets Manager. Install with: pip install boto3")

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DecryptionFailureException':
                raise Exception(f"Secrets Manager can't decrypt the secret using the provided KMS key: {e}")
            elif error_code == 'InternalServiceErrorException':
                raise Exception(f"An error occurred on the server side: {e}")
            elif error_code == 'InvalidParameterException':
                raise Exception(f"Invalid parameter in request: {e}")
            elif error_code == 'InvalidRequestException':
                raise Exception(f"Invalid request: {e}")
            elif error_code == 'ResourceNotFoundException':
                raise Exception(f"Secret '{secret_name}' not found in region '{region_name}': {e}")
            else:
                raise Exception(f"Error retrieving secret: {e}")

        # Parse the secret
        if 'SecretString' in get_secret_value_response:
            secret_string = get_secret_value_response['SecretString']
            try:
                return json.loads(secret_string)
            except json.JSONDecodeError:
                # If it's not JSON, treat as plain text
                logger.warning(f"Secret '{secret_name}' is not JSON format. Treating as plain text.")
                return {'value': secret_string}
        else:
            # Binary secret (not typical for application secrets)
            logger.warning(f"Secret '{secret_name}' is binary format, which is unusual for application secrets.")
            return {}

    @classmethod
    def get(cls, key: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Get secret value with fallback chain:
        1. AWS Secrets Manager (if enabled)
        2. Environment variable (if env_var specified or key as env var name)
        3. Legacy secrets.py (for backward compatibility)
        4. Default value

        Args:
            key: Secret key name
            default: Default value if not found
            env_var: Environment variable name (if different from key)

        Returns:
            Secret value

        Example:
            secrets.get('SECRET_KEY', env_var='DJANGO_SECRET_KEY')
        """
        # Ensure secrets are loaded
        if cls._secrets_cache is None:
            cls.load()

        # 1. Check AWS Secrets Manager cache
        if cls._use_aws and key in cls._secrets_cache:
            return cls._secrets_cache[key]

        # 2. Check environment variable
        env_key = env_var or key
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # 3. Check legacy secrets.py file
        try:
            from config import secrets as secrets_module
            if hasattr(secrets_module, key):
                return getattr(secrets_module, key)
        except (ImportError, AttributeError):
            pass

        # 4. Return default
        return default

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        Get all secrets from AWS Secrets Manager

        Returns:
            Dictionary of all secrets
        """
        if cls._secrets_cache is None:
            cls.load()
        return cls._secrets_cache.copy()

    @classmethod
    def reload(cls):
        """Force reload secrets"""
        cls._secrets_cache = None
        return cls.load(reload=True)

    @classmethod
    def clear(cls):
        """Clear cached secrets"""
        cls._secrets_cache = None
        cls._use_aws = False

    @classmethod
    def is_using_aws(cls) -> bool:
        """Check if using AWS Secrets Manager"""
        return cls._use_aws

    @classmethod
    def set(cls, key: str, value: Any):
        """
        Set secret value (runtime only, not persisted)
        Useful for testing

        Args:
            key: Secret key
            value: Secret value
        """
        if cls._secrets_cache is None:
            cls.load()
        cls._secrets_cache[key] = value


# Convenience instance
secrets = SecretsManager.load()
