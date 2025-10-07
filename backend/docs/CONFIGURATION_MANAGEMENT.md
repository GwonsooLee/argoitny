# Configuration Management Guide

This guide explains how AlgoItny backend manages configuration using a flexible multi-source approach.

## Table of Contents

- [Overview](#overview)
- [Configuration Sources](#configuration-sources)
- [Quick Start](#quick-start)
- [Configuration File Format](#configuration-file-format)
- [Environment Variables](#environment-variables)
- [Kubernetes Deployment](#kubernetes-deployment)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Migration Guide](#migration-guide)

## Overview

AlgoItny uses a **three-tier configuration system** with the following priority:

1. **Environment Variables** (highest priority) - for secrets and deployment-specific overrides
2. **Configuration File (YAML)** - for application configuration
3. **Default Values** (lowest priority) - fallback values

This approach provides:
- ✅ **Security**: Sensitive data in environment variables/Secrets, not in config files
- ✅ **Flexibility**: Easy to override for different environments
- ✅ **Kubernetes-ready**: Native ConfigMap and Secret support
- ✅ **Developer-friendly**: YAML config files are easy to read and edit
- ✅ **Backward compatible**: Still works with existing `secrets.py`

## Configuration Sources

### 1. Configuration File (YAML)

**Default locations** (checked in order):
1. Path specified in `CONFIG_FILE` environment variable
2. `/etc/algoitny/config.yaml` (Kubernetes ConfigMap mount point)
3. `config/config.yaml` (project config directory)
4. `config.yaml` (project root)

**Example:**
```yaml
django:
  debug: false
  allowed_hosts:
    - api.testcase.run

database:
  host: mysql-service
  port: 3306
  name: algoitny

cache:
  enable_redis: true
  redis:
    host: redis-service
    port: 6379
```

### 2. Environment Variables

Environment variables take **precedence** over config file values.

**Example:**
```bash
export SECRET_KEY="your-secret-key"
export DB_PASSWORD="secure-password"
export GEMINI_API_KEY="your-api-key"
```

### 3. secrets.py (Legacy)

For backward compatibility, `config/secrets.py` is still supported for sensitive data.

**Priority:** `secrets.py` > Config File > Environment Variables > Defaults

## Quick Start

### Local Development

1. **Copy example configuration:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. **Edit configuration:**
   ```bash
   vim config/config.yaml
   ```

3. **Set sensitive data as environment variables:**
   ```bash
   export SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
   export DB_PASSWORD="your-db-password"
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

4. **Run the application:**
   ```bash
   python manage.py runserver
   ```

### Production Deployment

1. **Create configuration file** with non-sensitive settings
2. **Store secrets** in environment variables or secure vault
3. **Set `CONFIG_FILE`** environment variable if using custom path

## Configuration File Format

### Complete Example

See `config/config.example.yaml` for a complete annotated example.

### Key Sections

#### Django Settings
```yaml
django:
  secret_key: ""  # Leave empty, use env var
  debug: false
  allowed_hosts:
    - api.example.com
  timezone: "UTC"
  language_code: "en-us"
```

#### Database
```yaml
database:
  engine: "django.db.backends.mysql"
  name: "algoitny"
  user: "algoitny"
  password: ""  # Leave empty, use env var
  host: "localhost"
  port: 3306
  conn_max_age: 600
  conn_health_checks: true
```

#### Cache
```yaml
cache:
  enable_redis: true
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: ""  # Leave empty, use env var
    max_connections: 50

  ttl:
    problem_list: 300
    problem_detail: 600
```

#### Celery
```yaml
celery:
  broker_url: "redis://localhost:6379/0"
  result_backend: "django-db"
  task_time_limit: 1800
  worker_concurrency: 4
```

#### Security
```yaml
security:
  csrf_trusted_origins:
    - https://api.example.com
  secure_ssl_redirect: true
  secure_hsts_seconds: 31536000
  admin_emails:
    - admin@example.com
```

## Environment Variables

### Required Variables

These must be set as environment variables (never in config files):

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DB_PASSWORD` | Database password | `secure-password-123` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `GOOGLE_CLIENT_ID` | OAuth client ID | `123...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth secret | `GOCSPX-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONFIG_FILE` | Path to config file | Auto-detect |
| `DEBUG` | Debug mode | `true` |
| `ENABLE_REDIS_CACHE` | Use Redis cache | `false` |
| `REDIS_PASSWORD` | Redis password | (empty) |
| `EMAIL_HOST_PASSWORD` | SMTP password | (empty) |

### Generating SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Kubernetes Deployment

### ConfigMap for Application Settings

Create a ConfigMap from your config file:

```bash
kubectl create configmap algoitny-backend-config \
  --from-file=config.yaml=config/config.yaml \
  --namespace=default
```

Or use the provided manifest:

```bash
kubectl apply -f k8s/configmap.yaml
```

### Secret for Sensitive Data

Create a Secret for sensitive values:

```bash
kubectl create secret generic algoitny-backend-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=DB_PASSWORD='your-db-password' \
  --from-literal=GEMINI_API_KEY='your-gemini-key' \
  --namespace=default
```

### Deployment Configuration

Example deployment using both ConfigMap and Secret:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: algoitny-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: algoitny/backend:latest

        # Environment variables from Secret
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: algoitny-backend-secrets
              key: SECRET_KEY
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: algoitny-backend-secrets
              key: DB_PASSWORD

        # Mount ConfigMap as file
        volumeMounts:
        - name: config
          mountPath: /etc/algoitny
          readOnly: true

      volumes:
      - name: config
        configMap:
          name: algoitny-backend-config
          items:
          - key: config.yaml
            path: config.yaml
```

### Updating Configuration

**Update ConfigMap:**
```bash
kubectl edit configmap algoitny-backend-config
# Or
kubectl apply -f k8s/configmap.yaml
```

**Reload pods** (ConfigMaps don't auto-reload):
```bash
kubectl rollout restart deployment algoitny-backend
```

**Update Secret:**
```bash
kubectl edit secret algoitny-backend-secrets
# Values must be base64 encoded
```

## API Reference

### ConfigLoader

```python
from api.utils.config import ConfigLoader

# Load configuration
config = ConfigLoader.load()

# Get values
value = config.get('database.host')
debug = config.get_bool('django.debug')
port = config.get_int('database.port')
hosts = config.get_list('django.allowed_hosts')
ttl_config = config.get_dict('cache.ttl')

# With environment variable fallback
db_host = config.get('database.host', env_var='DB_HOST', default='localhost')

# Reload configuration
config.reload()

# Runtime modifications (for testing)
config.set('test.key', 'test-value')

# Clear cache
ConfigLoader.clear()
```

### Method Reference

#### `load(config_path=None, reload=False)`
Load configuration from file or cache.

**Parameters:**
- `config_path` (str, optional): Path to config file
- `reload` (bool): Force reload even if cached

**Returns:** ConfigLoader instance

#### `get(key, default=None, env_var=None)`
Get configuration value.

**Parameters:**
- `key` (str): Dot-separated key (e.g., 'database.host')
- `default` (any): Default value if not found
- `env_var` (str, optional): Environment variable name to check first

**Returns:** Configuration value

#### `get_bool(key, default=False, env_var=None)`
Get boolean value. Converts strings like 'true', 'false', '1', '0'.

#### `get_int(key, default=0, env_var=None)`
Get integer value with automatic conversion.

#### `get_list(key, default=None, env_var=None, separator=',')`
Get list value. From config file as YAML list, or from env var as comma-separated string.

#### `get_dict(key, default=None)`
Get dictionary value.

#### `reload()`
Force reload configuration from file.

#### `set(key, value)`
Set runtime configuration value (not persisted).

#### `clear()`
Clear cached configuration.

#### `get_all()`
Get complete configuration dictionary.

## Testing

### Running Configuration Tests

```bash
# Run all config tests
pytest tests/test_config.py -v

# Run specific test class
pytest tests/test_config.py::TestConfigLoader -v

# Run with coverage
pytest tests/test_config.py --cov=api.utils.config --cov-report=html
```

### Test Coverage

The test suite covers:
- ✅ Loading from YAML files
- ✅ Environment variable overrides
- ✅ Default values
- ✅ Type conversions (bool, int, list, dict)
- ✅ Nested key access
- ✅ Reload functionality
- ✅ Kubernetes ConfigMap simulation
- ✅ Error handling (malformed YAML, missing files)
- ✅ Thread safety
- ✅ Edge cases

### Example Test

```python
def test_config_loading():
    """Test loading configuration"""
    from api.utils.config import ConfigLoader

    config = ConfigLoader.load(config_path='config/config.yaml')

    # Test values
    assert config.get('django.debug') is False
    assert config.get_int('database.port') == 3306
    assert 'localhost' in config.get_list('django.allowed_hosts')
```

## Migration Guide

### From Environment Variables Only

**Before:**
```python
# settings.py
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
```

**After:**
```python
# settings.py
from api.utils.config import ConfigLoader
config = ConfigLoader.load()

DEBUG = config.get_bool('django.debug', env_var='DEBUG', default=True)
ALLOWED_HOSTS = config.get_list('django.allowed_hosts', env_var='ALLOWED_HOSTS', default=['localhost'])
```

```yaml
# config/config.yaml
django:
  debug: false
  allowed_hosts:
    - api.example.com
    - example.com
```

### From secrets.py

**Before:**
```python
# config/secrets.py
SECRET_KEY = 'my-secret-key'
DB_PASSWORD = 'my-db-password'
```

**After (recommended):**
```bash
# Environment variables
export SECRET_KEY="my-secret-key"
export DB_PASSWORD="my-db-password"
```

```python
# settings.py - automatic fallback to secrets.py if exists
SECRET_KEY = SECRETS_SECRET_KEY or config.get('django.secret_key', env_var='SECRET_KEY')
```

**Note:** `secrets.py` is still supported for backward compatibility.

### From Hardcoded Values

**Before:**
```python
# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_TASK_TIME_LIMIT = 1800
```

**After:**
```python
# settings.py
CELERY_BROKER_URL = config.get('celery.broker_url', default='redis://localhost:6379/0')
CELERY_TASK_TIME_LIMIT = config.get_int('celery.task_time_limit', default=1800)
```

```yaml
# config/config.yaml
celery:
  broker_url: "redis://redis-service:6379/0"
  task_time_limit: 1800
```

## Best Practices

### 1. Security

✅ **DO:**
- Store secrets in environment variables or Kubernetes Secrets
- Use `.gitignore` to exclude `config/config.yaml` (not `config.example.yaml`)
- Rotate secrets regularly

❌ **DON'T:**
- Commit secrets to version control
- Put passwords in config files
- Share production config files

### 2. Configuration Organization

✅ **DO:**
- Use `config.example.yaml` as template with dummy values
- Document all configuration options with comments
- Group related settings together
- Use meaningful key names

❌ **DON'T:**
- Mix application config with secrets
- Use cryptic abbreviations
- Create deep nesting (max 3 levels recommended)

### 3. Environment-Specific Configuration

**Development:**
```yaml
django:
  debug: true
cache:
  enable_redis: false  # Use local memory cache
```

**Staging:**
```yaml
django:
  debug: false
cache:
  enable_redis: true
monitoring:
  environment: "staging"
```

**Production:**
```yaml
django:
  debug: false
cache:
  enable_redis: true
security:
  secure_ssl_redirect: true
monitoring:
  environment: "production"
```

### 4. Validation

Add validation in `settings.py`:

```python
# Validate required secrets
if not SECRET_KEY or SECRET_KEY == 'django-insecure-change-this-in-production':
    raise ImproperlyConfigured("SECRET_KEY must be set in production")

if not DEBUG and not GEMINI_API_KEY:
    raise ImproperlyConfigured("GEMINI_API_KEY is required in production")
```

## Troubleshooting

### Configuration Not Loading

**Check file location:**
```python
from api.utils.config import ConfigLoader
config = ConfigLoader.load()
print(f"Config path: {ConfigLoader._config_path}")
```

**Verify CONFIG_FILE environment variable:**
```bash
echo $CONFIG_FILE
```

**Check file permissions (Kubernetes):**
```bash
kubectl exec -it <pod-name> -- ls -la /etc/algoitny/
```

### Environment Variables Not Working

**Verify env var is set:**
```bash
docker exec <container> env | grep SECRET_KEY
kubectl exec <pod> -- env | grep SECRET_KEY
```

**Check priority:**
Remember: Env Var > Config File > Default

### Values Not Updating

**Reload configuration:**
```python
from api.utils.config import ConfigLoader
ConfigLoader.reload()
```

**Restart application:**
```bash
# Docker
docker restart algoitny-backend

# Kubernetes
kubectl rollout restart deployment algoitny-backend
```

### Type Conversion Issues

```python
# Use typed getters
port = config.get_int('database.port')  # Returns int
debug = config.get_bool('django.debug')  # Returns bool
hosts = config.get_list('django.allowed_hosts')  # Returns list

# Not recommended
port = config.get('database.port')  # Might return string
```

## Additional Resources

- **Example Config**: `config/config.example.yaml`
- **Kubernetes Manifests**: `k8s/configmap.yaml`
- **Tests**: `tests/test_config.py`
- **API Documentation**: This file (API Reference section)

## Support

For issues or questions:
1. Check existing documentation
2. Review test cases for examples
3. Check application logs
4. Create an issue with configuration details (sanitized)

---

**Last Updated:** 2025-10-07
**Version:** 1.0.0
