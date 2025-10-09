"""
Secrets management for both local and production environments.
Local: Uses .env file
Production: Uses AWS Secrets Manager
"""
import os
import json
from dotenv import load_dotenv

# Load .env file in local environment
# Try root .env first (for local dev), then backend/.env
from pathlib import Path
root_env = Path(__file__).resolve().parent.parent.parent / '.env'
if root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()


def get_secret(secret_name, default=None):
    """
    Get secret from environment or AWS Secrets Manager.

    Priority:
    1. Environment variable (local development)
    2. AWS Secrets Manager (production)
    3. Default value
    """
    # Try environment variable first (local)
    env_value = os.getenv(secret_name)
    if env_value:
        return env_value

    # Try AWS Secrets Manager (production)
    if os.getenv('USE_SECRETS_MANAGER', 'false').lower() == 'true':
        try:
            import boto3
            from botocore.exceptions import ClientError

            secrets_name = os.getenv('AWS_SECRET_NAME', 'algoitny/prod')
            region_name = os.getenv('AWS_REGION', 'us-east-1')

            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=region_name
            )

            try:
                get_secret_value_response = client.get_secret_value(
                    SecretId=secrets_name
                )
            except ClientError as e:
                print(f"Error retrieving secret from AWS: {e}")
                return default

            # Parse the secret
            if 'SecretString' in get_secret_value_response:
                secret = json.loads(get_secret_value_response['SecretString'])
                return secret.get(secret_name, default)

        except Exception as e:
            print(f"Error accessing Secrets Manager: {e}")
            return default

    return default


# Pre-load critical secrets
SECRET_KEY = get_secret('DJANGO_SECRET_KEY', 'django-insecure-local-dev-key-change-in-production')
GEMINI_API_KEY = get_secret('GEMINI_API_KEY', '')
GOOGLE_CLIENT_ID = get_secret('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = get_secret('GOOGLE_CLIENT_SECRET', '')
