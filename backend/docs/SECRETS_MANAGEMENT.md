# Secrets Management Guide

This guide explains how AlgoItny backend manages **sensitive data** (passwords, API keys, credentials) separately from application configuration.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [AWS Secrets Manager](#aws-secrets-manager)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [API Reference](#api-reference)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

AlgoItny uses **SecretsManager** utility to load sensitive data with the following priority:

1. **AWS Secrets Manager** (production) - centralized secret management
2. **Environment Variables** (fallback) - for local development and containers
3. **Legacy secrets.py** (fallback) - backward compatibility

### Why Separate Secrets from Configuration?

✅ **Security**
- Sensitive data never stored in config files or version control
- Centralized secret management with AWS Secrets Manager
- Automatic encryption at rest and in transit

✅ **Compliance**
- Meets security audit requirements
- Supports secret rotation
- Access control via IAM policies

✅ **Flexibility**
- Different secrets for different environments
- Easy secret updates without code deployment
- Supports multiple secret backends

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SecretsManager                        │
│                                                          │
│  Priority Order:                                         │
│  1. AWS Secrets Manager (if USE_SECRETS_MANAGER=true)  │
│  2. Environment Variables                               │
│  3. Legacy secrets.py file                              │
│  4. Default values                                       │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                     settings.py                          │
│                                                          │
│  SECRET_KEY = secrets.get('SECRET_KEY')                 │
│  DB_PASSWORD = secrets.get('DB_PASSWORD')               │
│  GEMINI_API_KEY = secrets.get('GEMINI_API_KEY')        │
└─────────────────────────────────────────────────────────┘
```

### Secrets vs Configuration

| Type | Storage | Examples | Updated |
|------|---------|----------|---------|
| **Secrets** (SecretsManager) | AWS Secrets Manager / Env Vars | Passwords, API keys, tokens | Rarely, via AWS console |
| **Configuration** (ConfigLoader) | YAML files / ConfigMaps | URLs, timeouts, feature flags | Frequently, via code deployment |

## Quick Start

### For Local Development

```bash
# Set required secrets as environment variables
export SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
export DB_PASSWORD="your-local-db-password"
export GEMINI_API_KEY="your-gemini-api-key"
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Run application
python manage.py runserver
```

### For Production (AWS)

```bash
# Enable AWS Secrets Manager
export USE_SECRETS_MANAGER=true
export AWS_SECRET_NAME=algoitny-secrets
export AWS_REGION=us-east-1

# Run application (will load secrets from AWS)
gunicorn config.wsgi
```

## AWS Secrets Manager

### Creating Secrets in AWS

#### Option 1: AWS Console

1. Go to **AWS Secrets Manager** console
2. Click **Store a new secret**
3. Choose **Other type of secret**
4. Add key-value pairs:
   ```json
   {
     "SECRET_KEY": "your-django-secret-key",
     "DB_PASSWORD": "your-database-password",
     "GEMINI_API_KEY": "your-gemini-api-key",
     "GOOGLE_CLIENT_ID": "your-google-client-id",
     "GOOGLE_CLIENT_SECRET": "your-google-client-secret",
     "REDIS_PASSWORD": "your-redis-password",
     "EMAIL_HOST_USER": "your-email@gmail.com",
     "EMAIL_HOST_PASSWORD": "your-email-app-password",
     "JUDGE0_API_KEY": "your-judge0-key",
     "SENTRY_DSN": "your-sentry-dsn"
   }
   ```
5. Name the secret: `algoitny-secrets`
6. Configure rotation (optional)
7. Review and store

#### Option 2: AWS CLI

```bash
# Create secret
aws secretsmanager create-secret \
  --name algoitny-secrets \
  --description "AlgoItny Backend Secrets" \
  --secret-string file://secrets.json \
  --region us-east-1
```

**secrets.json:**
```json
{
  "SECRET_KEY": "your-django-secret-key",
  "DB_PASSWORD": "your-database-password",
  "GEMINI_API_KEY": "your-gemini-api-key",
  "GOOGLE_CLIENT_ID": "your-google-client-id",
  "GOOGLE_CLIENT_SECRET": "your-google-client-secret"
}
```

#### Option 3: Terraform

```hcl
resource "aws_secretsmanager_secret" "algoitny_secrets" {
  name        = "algoitny-secrets"
  description = "AlgoItny Backend Secrets"
}

resource "aws_secretsmanager_secret_version" "algoitny_secrets" {
  secret_id = aws_secretsmanager_secret.algoitny_secrets.id
  secret_string = jsonencode({
    SECRET_KEY              = var.secret_key
    DB_PASSWORD            = var.db_password
    GEMINI_API_KEY         = var.gemini_api_key
    GOOGLE_CLIENT_ID       = var.google_client_id
    GOOGLE_CLIENT_SECRET   = var.google_client_secret
  })
}
```

### Updating Secrets

#### AWS Console
1. Go to AWS Secrets Manager
2. Select `algoitny-secrets`
3. Click **Retrieve secret value**
4. Click **Edit**
5. Modify values
6. Click **Save**
7. **Restart application** to load new values

#### AWS CLI
```bash
# Update secret
aws secretsmanager update-secret \
  --secret-id algoitny-secrets \
  --secret-string file://secrets-updated.json \
  --region us-east-1

# Restart application
kubectl rollout restart deployment algoitny-backend
```

### IAM Permissions

The application needs IAM permissions to read secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:algoitny-secrets-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/your-kms-key-id",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```

**For EC2/ECS/EKS**: Attach this policy to the IAM role assigned to your instances/pods.

## Environment Variables

### Required Secrets

These must be set either in AWS Secrets Manager or as environment variables:

| Secret | Description | Example |
|--------|-------------|---------|
| `SECRET_KEY` | Django secret key | Generated with Django utility |
| `DB_PASSWORD` | Database password | `SecurePass123!` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `GOOGLE_CLIENT_ID` | OAuth client ID | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | `GOCSPX-...` |

### Optional Secrets

| Secret | Description | Default |
|--------|-------------|---------|
| `REDIS_PASSWORD` | Redis password | (empty) |
| `EMAIL_HOST_USER` | SMTP username | (empty) |
| `EMAIL_HOST_PASSWORD` | SMTP password | (empty) |
| `JUDGE0_API_KEY` | Judge0 API key | (empty) |
| `SENTRY_DSN` | Sentry DSN | (empty) |

### Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_SECRETS_MANAGER` | Enable AWS Secrets Manager | `false` |
| `AWS_SECRET_NAME` | Secret name in AWS | `algoitny-secrets` |
| `AWS_REGION` | AWS region | `us-east-1` |

## Local Development

### Method 1: Environment Variables (.env file)

Create `.env` file in project root:

```bash
# Django
SECRET_KEY=your-local-secret-key
DEBUG=true

# Database
DB_PASSWORD=local-db-password

# Google Services
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional
REDIS_PASSWORD=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

Load with:
```bash
export $(cat .env | xargs)
python manage.py runserver
```

### Method 2: Export Directly

```bash
#!/bin/bash
# dev-secrets.sh

export SECRET_KEY="dev-secret-key-$(openssl rand -hex 32)"
export DB_PASSWORD="dev-db-password"
export GEMINI_API_KEY="your-dev-gemini-key"
export GOOGLE_CLIENT_ID="your-dev-google-client-id"
export GOOGLE_CLIENT_SECRET="your-dev-google-client-secret"
```

Run:
```bash
source dev-secrets.sh
python manage.py runserver
```

### Method 3: Legacy secrets.py (Not Recommended)

Create `config/secrets.py`:

```python
# DO NOT commit this file to version control
SECRET_KEY = 'your-local-secret-key'
DB_PASSWORD = 'local-db-password'
DB_HOST = 'localhost'
DB_NAME = 'algoitny'
DB_USER = 'algoitny'
GEMINI_API_KEY = 'your-gemini-api-key'
GOOGLE_CLIENT_ID = 'your-google-client-id'
GOOGLE_CLIENT_SECRET = 'your-google-client-secret'
```

**Note**: This method is deprecated and kept only for backward compatibility.

## Production Deployment

### AWS ECS/EKS

#### Option 1: AWS Secrets Manager (Recommended)

**Environment variables for container:**
```yaml
environment:
  - name: USE_SECRETS_MANAGER
    value: "true"
  - name: AWS_SECRET_NAME
    value: "algoitny-secrets"
  - name: AWS_REGION
    value: "us-east-1"
```

**IAM Role**: Attach Secrets Manager read policy to task role.

#### Option 2: Environment Variables from Secrets

**ECS Task Definition:**
```json
{
  "containerDefinitions": [{
    "name": "backend",
    "secrets": [
      {
        "name": "SECRET_KEY",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123:secret:algoitny-secrets:SECRET_KEY::"
      },
      {
        "name": "DB_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123:secret:algoitny-secrets:DB_PASSWORD::"
      }
    ]
  }]
}
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: backend
    env:
    - name: SECRET_KEY
      valueFrom:
        secretKeyRef:
          name: algoitny-secrets
          key: SECRET_KEY
```

### Kubernetes with External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: algoitny-backend

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: algoitny-backend-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: algoitny-backend-secrets
  data:
  - secretKey: SECRET_KEY
    remoteRef:
      key: algoitny-secrets
      property: SECRET_KEY
  - secretKey: DB_PASSWORD
    remoteRef:
      key: algoitny-secrets
      property: DB_PASSWORD
```

## API Reference

### SecretsManager

```python
from api.utils.secrets import SecretsManager

# Load secrets
secrets = SecretsManager.load()

# Get secret value
secret_key = secrets.get('SECRET_KEY')
db_password = secrets.get('DB_PASSWORD', default='fallback')

# With explicit env var
api_key = secrets.get('API_KEY', env_var='CUSTOM_API_KEY_VAR')

# Get all secrets
all_secrets = secrets.get_all()

# Reload secrets
secrets.reload()

# Check if using AWS
if SecretsManager.is_using_aws():
    print("Using AWS Secrets Manager")

# Runtime set (for testing)
SecretsManager.set('TEST_SECRET', 'test-value')

# Clear cache
SecretsManager.clear()
```

### Method Reference

#### `load(secret_name=None, region_name=None, reload=False)`

Load secrets from AWS Secrets Manager or environment variables.

**Parameters:**
- `secret_name` (str, optional): AWS secret name (default: from `AWS_SECRET_NAME` env var)
- `region_name` (str, optional): AWS region (default: from `AWS_REGION` env var or 'us-east-1')
- `reload` (bool): Force reload even if cached

**Returns:** SecretsManager instance

#### `get(key, default=None, env_var=None)`

Get secret value with fallback chain.

**Priority:**
1. AWS Secrets Manager (if enabled)
2. Environment variable
3. Legacy secrets.py
4. Default value

**Parameters:**
- `key` (str): Secret key name
- `default` (any): Default value if not found
- `env_var` (str, optional): Environment variable name to check

**Returns:** Secret value

#### `get_all()`

Get all secrets from AWS Secrets Manager.

**Returns:** Dictionary of all secrets

#### `reload()`

Force reload secrets from source.

#### `clear()`

Clear cached secrets.

#### `is_using_aws()`

Check if using AWS Secrets Manager.

**Returns:** Boolean

#### `set(key, value)`

Set secret value at runtime (not persisted). Useful for testing.

## Security Best Practices

### 1. Never Commit Secrets

❌ **DON'T:**
```python
# config/secrets.py (committed to Git)
SECRET_KEY = 'actual-secret-key-123'
```

✅ **DO:**
- Use AWS Secrets Manager for production
- Use environment variables for local development
- Add `config/secrets.py` to `.gitignore`

### 2. Use Strong Secret Keys

```bash
# Generate secure SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Generate secure password
openssl rand -base64 32
```

### 3. Rotate Secrets Regularly

- Enable automatic rotation in AWS Secrets Manager
- Update application after rotation (restart pods/containers)
- Test rotation in staging first

### 4. Principle of Least Privilege

```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"  // Read-only
  ],
  "Resource": "arn:aws:secretsmanager:*:*:secret:algoitny-secrets-*"
}
```

### 5. Separate Secrets per Environment

- `algoitny-secrets-dev`
- `algoitny-secrets-staging`
- `algoitny-secrets-prod`

### 6. Monitor Secret Access

Enable AWS CloudTrail logging for Secrets Manager:

```bash
# View secret access logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=algoitny-secrets \
  --max-results 10
```

### 7. Use AWS KMS for Encryption

Create custom KMS key for additional security:

```bash
aws kms create-key \
  --description "AlgoItny Secrets Encryption Key" \
  --key-policy file://key-policy.json
```

### 8. Audit Secret Usage

```python
# In Django shell
from api.utils.secrets import SecretsManager

secrets = SecretsManager.load()
if SecretsManager.is_using_aws():
    print("✅ Using AWS Secrets Manager")
else:
    print("⚠️  Using environment variables")
```

## Troubleshooting

### Secrets Not Loading

**Check AWS Secrets Manager is enabled:**
```bash
echo $USE_SECRETS_MANAGER  # Should be 'true'
```

**Verify IAM permissions:**
```bash
aws secretsmanager get-secret-value --secret-id algoitny-secrets
```

**Check secret exists:**
```bash
aws secretsmanager list-secrets --filters Key=name,Values=algoitny-secrets
```

### Permission Denied Error

```
ClientError: An error occurred (AccessDeniedException) when calling the GetSecretValue operation
```

**Solution:** Add IAM policy to task role/instance profile.

### Secret Not Found

```
ClientError: An error occurred (ResourceNotFoundException) when calling the GetSecretValue operation
```

**Solution:**
1. Verify secret name: `echo $AWS_SECRET_NAME`
2. Check region: `echo $AWS_REGION`
3. Create secret if missing

### Application Still Using Old Secrets

**Solution:** Restart application after updating secrets:

```bash
# Docker
docker restart algoitny-backend

# Kubernetes
kubectl rollout restart deployment algoitny-backend

# ECS
aws ecs update-service --cluster algoitny --service backend --force-new-deployment
```

### Boto3 Import Error

```
ImportError: No module named 'boto3'
```

**Solution:** Install boto3:
```bash
pip install boto3
```

### Fallback to Environment Variables

If AWS Secrets Manager fails, the application automatically falls back to environment variables:

```python
# This will work as fallback
export SECRET_KEY="fallback-secret-key"
```

Check logs:
```
WARNING: Failed to load from AWS Secrets Manager. Falling back to environment variables.
```

## Testing

### Unit Tests

```bash
# Run secrets tests
pytest tests/test_secrets.py -v

# With coverage
pytest tests/test_secrets.py --cov=api.utils.secrets --cov-report=html
```

### Integration Test

```python
# tests/test_secrets_integration.py
def test_load_from_aws():
    """Test loading secrets from AWS"""
    import os
    os.environ['USE_SECRETS_MANAGER'] = 'true'
    os.environ['AWS_SECRET_NAME'] = 'algoitny-secrets-test'

    from api.utils.secrets import SecretsManager
    SecretsManager.clear()
    secrets = SecretsManager.load()

    assert secrets.get('SECRET_KEY') is not None
```

### Manual Test in Django Shell

```bash
python manage.py shell
```

```python
from api.utils.secrets import SecretsManager

# Load secrets
secrets = SecretsManager.load()

# Check source
if SecretsManager.is_using_aws():
    print("Loading from AWS Secrets Manager")
else:
    print("Loading from environment variables")

# Get values
print(f"SECRET_KEY: {secrets.get('SECRET_KEY')[:10]}...")
print(f"DB_PASSWORD: {'***' if secrets.get('DB_PASSWORD') else 'Not set'}")

# Get all secrets (be careful in production!)
all_secrets = secrets.get_all()
print(f"Total secrets loaded: {len(all_secrets)}")
```

## Migration Guide

### From Environment Variables Only

**Before:**
```bash
export SECRET_KEY="..."
export DB_PASSWORD="..."
```

**After (Production):**
1. Create AWS Secrets Manager secret
2. Add all secrets to AWS
3. Set `USE_SECRETS_MANAGER=true`
4. Remove individual env vars (optional)

### From secrets.py File

**Before:**
```python
# config/secrets.py
SECRET_KEY = "..."
DB_PASSWORD = "..."
```

**After:**
1. Create AWS Secrets Manager secret
2. Copy values from secrets.py to AWS
3. Delete secrets.py file
4. Set `USE_SECRETS_MANAGER=true`

**Note:** secrets.py still works as fallback, but not recommended.

## Additional Resources

- **AWS Secrets Manager Documentation**: https://docs.aws.amazon.com/secretsmanager/
- **AWS SDK for Python (Boto3)**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **Test Suite**: `tests/test_secrets.py`
- **Source Code**: `api/utils/secrets.py`

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review test cases in `tests/test_secrets.py`
3. Check AWS CloudWatch Logs
4. Verify IAM permissions
5. Create issue with sanitized error logs

---

**Last Updated:** 2025-10-07
**Version:** 1.0.0
