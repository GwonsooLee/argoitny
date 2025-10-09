"""
Test settings for AlgoItny project.
Inherits from main settings and overrides for testing.
"""
from .settings import *

# Override settings for testing
DEBUG = True
# Use consistent SECRET_KEY for JWT token signing/verification
SECRET_KEY = 'django-insecure-change-this-in-production'
ALLOWED_HOSTS = ['*']  # Allow all hosts for testing

# Use in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
    }
}

# Use Celery eager mode for tests (synchronous execution)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['null'],
            'level': 'CRITICAL',
        },
    },
}

# Disable password validation for tests
AUTH_PASSWORD_VALIDATORS = []

# Speed up password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Cache settings for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# DynamoDB settings for tests (use LocalStack)
LOCALSTACK_URL = os.getenv('LOCALSTACK_URL', 'http://localhost:4566')
AWS_ACCESS_KEY_ID = 'test'
AWS_SECRET_ACCESS_KEY = 'test'
AWS_DEFAULT_REGION = 'us-east-1'

# Override any external API keys with test values
GOOGLE_OAUTH_CLIENT_ID = 'test-google-client-id'
GOOGLE_OAUTH_CLIENT_SECRET = 'test-google-client-secret'
GEMINI_API_KEY = 'test-gemini-api-key'
JUDGE0_API_KEY = 'test-judge0-api-key'
