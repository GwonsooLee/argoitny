"""
Django settings for AlgoItny project.

This settings file uses:
1. SecretsManager - for sensitive data (passwords, API keys, secrets)
   - AWS Secrets Manager (production)
   - Environment variables (fallback)
   - secrets.py (legacy fallback)

2. ConfigLoader - for non-sensitive configuration
   - YAML configuration file (config/config.yaml or /etc/algoitny/config.yaml)
   - Environment variables (fallback)
   - Default values

For Kubernetes deployments:
- Mount ConfigMap to /etc/algoitny/config.yaml (non-sensitive config)
- Use Kubernetes Secrets as environment variables (sensitive data)
"""
from pathlib import Path
from datetime import timedelta
import sys
import os

# Add parent directory to path for config loader
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load configuration and secrets
from api.utils.config import ConfigLoader
from api.utils.secrets import SecretsManager

config = ConfigLoader.load()
secrets = SecretsManager.load()

# ============================================
# Django Core Settings
# ============================================

# Secret key (from Secrets Manager or environment variable)
SECRET_KEY = secrets.get('SECRET_KEY', default='django-insecure-change-this-in-production')

# Debug mode
DEBUG = config.get_bool('django.debug', env_var='DEBUG', default=True)

# Allowed hosts
ALLOWED_HOSTS = config.get_list(
    'django.allowed_hosts',
    env_var='ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1']
)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_results',
    'api',
]

# Add debug toolbar if enabled
if config.get_bool('middleware.enable_debug_toolbar', env_var='ENABLE_DEBUG_TOOLBAR', default=False):
    INSTALLED_APPS.append('debug_toolbar')
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Custom user model removed - using DynamoDB with custom authentication backend
# AUTH_USER_MODEL = 'api.User'  # REMOVED - now using DynamoDB
# See: api/authentication.py (CustomJWTAuthentication)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]

# Add WhiteNoise middleware for static files in production
if config.get_bool('middleware.use_whitenoise', env_var='USE_WHITENOISE', default=False):
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')

# Add debug toolbar middleware if enabled
if config.get_bool('middleware.enable_debug_toolbar', env_var='ENABLE_DEBUG_TOOLBAR', default=False):
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

MIDDLEWARE.extend([
    'api.middleware.SecurityHeadersMiddleware',  # Security headers (COOP, COEP)
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])

ROOT_URLCONF = 'config.urls'

# ASGI Configuration - ASGI only mode
ASGI_APPLICATION = 'config.asgi.application'

# Enable async mode for Django (Django 4.1+)
# This allows async views and middleware to run natively
ASYNC_MODE = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================
# Database Configuration
# ============================================
# NOTE: This project uses DynamoDB as the primary database.
# SQLite is used as a dummy database only for Django's internal requirements
# (sessions, admin, etc.). All application data is stored in DynamoDB.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
    }
}

# ============================================
# Password Validation
# ============================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================
# Internationalization
# ============================================

LANGUAGE_CODE = config.get('django.language_code', default='en-us')
TIME_ZONE = config.get('django.timezone', env_var='TZ', default='UTC')
USE_I18N = True
USE_TZ = True

# ============================================
# Static Files
# ============================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Use WhiteNoise for static files in production
STATICFILES_STORAGE = config.get(
    'static_files.storage',
    env_var='STATICFILES_STORAGE',
    default='django.contrib.staticfiles.storage.StaticFilesStorage'
)

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Media storage backend
DEFAULT_FILE_STORAGE = config.get(
    'static_files.media_storage',
    env_var='DEFAULT_FILE_STORAGE',
    default='django.core.files.storage.FileSystemStorage'
)

# AWS S3 Configuration (optional)
USE_S3 = config.get_bool('aws.use_s3', env_var='USE_S3', default=False)
if USE_S3:
    AWS_ACCESS_KEY_ID = secrets.get('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = secrets.get('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = secrets.get('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = config.get('aws.s3.region', env_var='AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com' if AWS_STORAGE_BUCKET_NAME else None
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': config.get('aws.s3.cache_control', default='max-age=86400'),
    }

    if AWS_STORAGE_BUCKET_NAME:
        # Override storage backends to use S3
        STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ============================================
# Default Primary Key Field Type
# ============================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# CORS Configuration
# ============================================

CORS_ALLOWED_ORIGINS = config.get_list(
    'cors.allowed_origins',
    env_var='CORS_ALLOWED_ORIGINS',
    default=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost",
    ]
)

CORS_ALLOW_CREDENTIALS = config.get_bool('cors.allow_credentials', default=True)

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================
# REST Framework Configuration
# ============================================

# Map permission string to class
_permission_map = {
    'AllowAny': 'rest_framework.permissions.AllowAny',
    'IsAuthenticated': 'rest_framework.permissions.IsAuthenticated',
}
_default_permission = config.get('rest_framework.default_permission', env_var='REST_FRAMEWORK_DEFAULT_PERMISSION', default='AllowAny')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.authentication.CustomJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        _permission_map.get(_default_permission, 'rest_framework.permissions.AllowAny'),
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': config.get_int('rest_framework.page_size', default=20),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        # Throttling disabled for development
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config.get('rest_framework.throttling.anon_rate', env_var='ANON_RATE_LIMIT', default='2000/hour'),
        'user': config.get('rest_framework.throttling.user_rate', env_var='USER_RATE_LIMIT', default='5000/hour'),
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# ============================================
# JWT Configuration
# ============================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config.get_int('jwt.access_token_lifetime', default=60)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        minutes=config.get_int('jwt.refresh_token_lifetime', default=43200)
    ),
    'ROTATE_REFRESH_TOKENS': config.get_bool('jwt.rotate_refresh_tokens', default=True),
    'BLACKLIST_AFTER_ROTATION': config.get_bool('jwt.blacklist_after_rotation', default=False),
    'UPDATE_LAST_LOGIN': config.get_bool('jwt.update_last_login', default=True),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer',
    'TOKEN_VERIFY_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenVerifySerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenBlacklistSerializer',
    'SLIDING_TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer',
    'SLIDING_TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer',
    # Clock skew tolerance: Allow 30 seconds difference between client and server clocks
    'LEEWAY': timedelta(seconds=30),
}

# ============================================
# Google OAuth Configuration
# ============================================

# OAuth credentials from Secrets Manager
GOOGLE_OAUTH_CLIENT_ID = secrets.get('GOOGLE_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = secrets.get('GOOGLE_CLIENT_SECRET', default='')

# Redirect URI from config (non-sensitive)
GOOGLE_OAUTH_REDIRECT_URI = config.get(
    'google_oauth.redirect_uri',
    env_var='GOOGLE_OAUTH_REDIRECT_URI',
    default='http://localhost/auth/callback'
)

# ============================================
# LLM Service Configuration (Gemini & OpenAI)
# ============================================

# Gemini API key from Secrets Manager
GEMINI_API_KEY = secrets.get('GEMINI_API_KEY', default='')

# OpenAI API Configuration
OPENAI_API_KEY = secrets.get('OPENAI_API_KEY', default='')
# GPT-5 is the latest flagship model with advanced reasoning capabilities
# Uses reasoning_effort parameter instead of temperature for deterministic output
OPENAI_MODEL = config.get('openai.model', env_var='OPENAI_MODEL', default='gpt-5')

# Default LLM Service ('gemini' or 'openai')
# This determines which LLM service is used by default
# Individual tasks can override this if needed
DEFAULT_LLM_SERVICE = config.get('llm.default_service', env_var='DEFAULT_LLM_SERVICE', default='gemini')

# ============================================
# S3 Test Case Storage Configuration
# ============================================

# S3 bucket for storing large test cases
TESTCASE_S3_BUCKET = config.get(
    'aws.testcase_bucket',
    env_var='TESTCASE_S3_BUCKET',
    default='algoitny-testcases-zteapne2'
)

# ============================================
# Code Execution Configuration
# ============================================

CODE_EXECUTION_TIMEOUT = config.get_int(
    'application.code_execution_timeout',
    env_var='CODE_EXECUTION_TIMEOUT',
    default=5
)

# ============================================
# Admin Configuration
# ============================================

ADMIN_EMAILS = config.get_list(
    'application.admin_emails',
    env_var='ADMIN_EMAILS',
    default=[]
)

# ============================================
# Redis Configuration
# ============================================

# Redis configuration removed - using LocMemCache instead

# ============================================
# Cache Configuration
# ============================================

# Using LocMemCache for all environments (Redis removed)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': config.get_int('cache.default_timeout', default=300),
    }
}

# Cache TTL settings
CACHE_TTL = config.get_dict('cache.ttl', default={
    'PROBLEM_LIST': 60 * 5,
    'PROBLEM_DETAIL': 60 * 10,
    'USER_STATS': 60 * 3,
    'SEARCH_HISTORY': 60 * 2,
    'TEST_CASES': 60 * 15,
    'SHORT': 60,
    'MEDIUM': 60 * 5,
    'LONG': 60 * 30,
})

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = config.get_int('session.cookie_age', env_var='SESSION_COOKIE_AGE', default=3600)
SESSION_SAVE_EVERY_REQUEST = config.get_bool('session.save_every_request', default=False)
SESSION_COOKIE_SECURE = config.get_bool('session.cookie_secure', env_var='SESSION_COOKIE_SECURE', default=False)
SESSION_COOKIE_HTTPONLY = config.get_bool('session.cookie_httponly', default=True)
SESSION_COOKIE_SAMESITE = config.get('session.cookie_samesite', env_var='SESSION_COOKIE_SAMESITE', default='Lax')

# CSRF Configuration
CSRF_COOKIE_SECURE = config.get_bool('session.cookie_secure', env_var='CSRF_COOKIE_SECURE', default=False)
CSRF_COOKIE_HTTPONLY = config.get_bool('session.cookie_httponly', default=True)
CSRF_COOKIE_SAMESITE = config.get('session.cookie_samesite', env_var='CSRF_COOKIE_SAMESITE', default='Lax')

# ============================================
# Environment Configuration
# ============================================
# Define ENVIRONMENT early so it can be used in other settings
ENVIRONMENT = config.get('monitoring.environment', env_var='ENVIRONMENT', default='development')

# ============================================
# Celery Configuration
# ============================================

# Environment-specific AWS configuration
# In production: Use IAM roles (no credentials needed)
# In local/dev: Use LocalStack with test credentials
IS_PRODUCTION = ENVIRONMENT == 'production'

# ============================================
# SQS Configuration
# ============================================

# SQS Queue URL (optional - for direct queue access outside of Celery)
SQS_QUEUE_NAME = config.get(
    'aws.sqs.queue_name',
    env_var='SQS_QUEUE_NAME',
    default='algoitny-jobs-prod' if IS_PRODUCTION else 'algoitny-jobs-dev'
)

if IS_PRODUCTION:
    # Production: Use IAM roles, no credentials
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
    CELERY_BROKER_URL = config.get(
        'celery.broker_url',
        env_var='CELERY_BROKER_URL',
        default='sqs://'  # No credentials - uses IAM role
    )
else:
    # Local/Dev: Use LocalStack with test credentials
    LOCALSTACK_URL = os.getenv('LOCALSTACK_URL', 'http://localhost:4566')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    CELERY_BROKER_URL = config.get(
        'celery.broker_url',
        env_var='CELERY_BROKER_URL',
        default=f'sqs://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@'
    )

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'

# Serialization
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = config.get_int('celery.task_time_limit', default=1800)
CELERY_TASK_SOFT_TIME_LIMIT = config.get_int('celery.task_soft_time_limit', default=1680)
# CRITICAL: Set to False to ACK messages immediately on consume, preventing duplicate execution
# Combined with DynamoDB atomic updates, this ensures tasks are processed exactly once
# Messages are removed from queue immediately, preventing visibility timeout issues
CELERY_TASK_ACKS_LATE = config.get_bool('celery.task_acks_late', default=False)
CELERY_TASK_REJECT_ON_WORKER_LOST = config.get_bool('celery.task_reject_on_worker_lost', default=True)

# Worker optimization
# CRITICAL: Set to 1 to prevent workers from prefetching multiple tasks (reduces duplicate risk)
CELERY_WORKER_PREFETCH_MULTIPLIER = config.get_int('celery.worker_prefetch_multiplier', default=1)
CELERY_WORKER_MAX_TASKS_PER_CHILD = config.get_int('celery.worker_max_tasks_per_child', default=1000)
CELERY_WORKER_DISABLE_RATE_LIMITS = False
CELERY_WORKER_SEND_TASK_EVENTS = True

# Broker optimization
CELERY_BROKER_CONNECTION_RETRY = config.get_bool('celery.broker_connection_retry', default=True)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = config.get_bool('celery.broker_connection_retry_on_startup', default=True)
CELERY_BROKER_CONNECTION_MAX_RETRIES = config.get_int('celery.broker_connection_max_retries', default=10)
CELERY_BROKER_POOL_LIMIT = config.get_int('celery.broker_pool_limit', default=10)

# SQS specific configuration
if IS_PRODUCTION:
    # Production: Use real AWS SQS with IAM roles
    # Queue name will be: queue_name_prefix + queue_name = 'algoitny-jobs-prod'
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'region': AWS_DEFAULT_REGION,
        # With acks_late=False, messages are ACKed immediately on consume
        # visibility_timeout is now a safety buffer in case of unexpected issues
        # Set to task_time_limit * 2 for safety
        'visibility_timeout': 3600,  # 60 minutes (task_time_limit 30min * 2)
        'polling_interval': 1,  # 1 second
        'queue_name_prefix': 'algoitny-jobs-',
        'is_secure': True,  # Use HTTPS in production
        # Predefined queues to use the Terraform-created queue
        'predefined_queues': {
            'jobs': {
                'url': f'https://sqs.{AWS_DEFAULT_REGION}.amazonaws.com/{{account_id}}/{SQS_QUEUE_NAME}',
            }
        }
    }
else:
    # Local/Dev: Use LocalStack
    # Set environment variables for boto3 to use LocalStack
    os.environ['AWS_ENDPOINT_URL'] = LOCALSTACK_URL
    os.environ['AWS_ENDPOINT_URL_SQS'] = LOCALSTACK_URL

    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'region': AWS_DEFAULT_REGION,
        # With acks_late=False, messages are ACKed immediately on consume
        # visibility_timeout is now a safety buffer in case of unexpected issues
        # Set to task_time_limit * 2 for safety
        'visibility_timeout': 3600,  # 60 minutes (task_time_limit 30min * 2)
        'polling_interval': 1,  # 1 second
        'queue_name_prefix': 'algoitny-',
        'is_secure': False,
        'endpoint_url': LOCALSTACK_URL,  # Force LocalStack endpoint
        'sqs_client_kwargs': {
            'endpoint_url': LOCALSTACK_URL,
            'region_name': AWS_DEFAULT_REGION,
            'aws_access_key_id': AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
            'use_ssl': False
        }
    }

# Result backend optimization
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = config.get_int('celery.result_expires', default=86400)
CELERY_RESULT_COMPRESSION = config.get('celery.result_compression', default='gzip')

# Default queue configuration
# Queue name will be: queue_name_prefix + default_queue + environment suffix
# Example: algoitny-jobs-prod (production) or algoitny-jobs (local)
CELERY_TASK_DEFAULT_QUEUE = 'jobs'

# Task routing for better load distribution
# All tasks use the same queue for now (algoitny-jobs-prod)
CELERY_TASK_ROUTES = {
    # High priority: User-facing tasks
    'api.tasks.execute_code_task': {'queue': 'jobs', 'priority': 8},

    # Medium priority: Background generation tasks
    'api.tasks.generate_script_task': {'queue': 'jobs', 'priority': 5},
    'api.tasks.generate_outputs_task': {'queue': 'jobs', 'priority': 5},

    # Medium-high priority: AI-powered tasks
    'api.tasks.generate_hints_task': {'queue': 'jobs', 'priority': 6},
    'api.tasks.extract_problem_info_task': {'queue': 'jobs', 'priority': 4},

    # Low priority: Maintenance and cache tasks
    'api.tasks.delete_job_task': {'queue': 'jobs', 'priority': 2},
    'api.tasks.warm_problem_cache_task': {'queue': 'jobs', 'priority': 3},
    'api.tasks.warm_user_stats_cache_task': {'queue': 'jobs', 'priority': 3},
    'api.tasks.invalidate_cache_task': {'queue': 'jobs', 'priority': 4},
}

# Task priority settings
CELERY_TASK_QUEUE_MAX_PRIORITY = config.get_int('celery.task_queue_max_priority', default=10)
CELERY_TASK_DEFAULT_PRIORITY = config.get_int('celery.task_default_priority', default=5)

# Beat scheduler configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Performance monitoring
CELERY_TASK_SEND_SENT_EVENT = True

# Override Celery for tests
if config.get_bool('testing.celery_eager', env_var='CELERY_TASK_ALWAYS_EAGER', default=False):
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
else:
    CELERY_TASK_ALWAYS_EAGER = False

# Broker transport options are defined above for SQS

# ============================================
# Judge0 API Configuration
# ============================================

USE_JUDGE0 = config.get_bool('api_keys.judge0.enabled', env_var='USE_JUDGE0', default=False)
JUDGE0_API_URL = config.get('api_keys.judge0.url', env_var='JUDGE0_API_URL', default='https://judge0-ce.p.rapidapi.com')
JUDGE0_API_KEY = secrets.get('JUDGE0_API_KEY', default='')  # From Secrets Manager

# ============================================
# Security Settings
# ============================================

CSRF_TRUSTED_ORIGINS = config.get_list(
    'security.csrf_trusted_origins',
    env_var='CSRF_TRUSTED_ORIGINS',
    default=[]
)

SECURE_SSL_REDIRECT = config.get_bool('security.secure_ssl_redirect', env_var='SECURE_SSL_REDIRECT', default=False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if SECURE_SSL_REDIRECT else None

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = config.get_int('security.secure_hsts_seconds', env_var='SECURE_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config.get_bool('security.secure_hsts_include_subdomains', default=True) if SECURE_HSTS_SECONDS > 0 else False
SECURE_HSTS_PRELOAD = config.get_bool('security.secure_hsts_preload', default=True) if SECURE_HSTS_SECONDS > 0 else False

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = config.get_bool('security.secure_content_type_nosniff', default=True)
SECURE_BROWSER_XSS_FILTER = config.get_bool('security.secure_browser_xss_filter', default=True)
X_FRAME_OPTIONS = config.get('security.x_frame_options', env_var='X_FRAME_OPTIONS', default='DENY')

# Additional security settings for production
DATA_UPLOAD_MAX_NUMBER_FIELDS = config.get_int('security.data_upload_max_number_fields', default=10000)

# ============================================
# Email Configuration
# ============================================

EMAIL_BACKEND = config.get('email.backend', env_var='EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config.get('email.smtp.host', env_var='EMAIL_HOST', default='localhost')
EMAIL_PORT = config.get_int('email.smtp.port', env_var='EMAIL_PORT', default=25)
EMAIL_USE_TLS = config.get_bool('email.smtp.use_tls', env_var='EMAIL_USE_TLS', default=False)

# Email credentials from Secrets Manager
EMAIL_HOST_USER = secrets.get('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = secrets.get('EMAIL_HOST_PASSWORD', default='')

# Email addresses (non-sensitive)
DEFAULT_FROM_EMAIL = config.get('email.default_from', env_var='DEFAULT_FROM_EMAIL', default='noreply@localhost')
SERVER_EMAIL = config.get('email.server_email', env_var='SERVER_EMAIL', default='root@localhost')

# ============================================
# Monitoring Configuration
# ============================================

# Sentry DSN from Secrets Manager
SENTRY_DSN = secrets.get('SENTRY_DSN', default='')

# ============================================
# Admin Configuration
# ============================================

# Admin email notifications
ADMINS = [
    (name_email.split(':')[0], name_email.split(':')[1])
    for name_email in config.get_list('application.admin_notifications', env_var='ADMINS', default=[])
    if ':' in name_email
]
MANAGERS = ADMINS

# Admin URL (configurable for security)
ADMIN_URL = config.get('application.admin_url', env_var='ADMIN_URL', default='admin/')

# ============================================
# Logging Configuration
# ============================================

LOG_TO_FILE = config.get_bool('logging.log_to_file', env_var='LOG_TO_FILE', default=False)
LOG_LEVEL = config.get('logging.level', env_var='LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else LOG_LEVEL,
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Reduce verbosity for OpenAI service logs
        'api.services.openai_service': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only show warnings and errors
            'propagate': False,
        },
    },
}

# Add file logging if enabled
if LOG_TO_FILE:
    LOG_DIR = config.get('logging.log_dir', env_var='LOG_DIR', default='/var/log/django')
    APP_LOG_FILE = config.get('logging.app_log_file', default='algoitny.log')
    ERROR_LOG_FILE = config.get('logging.error_log_file', default='error.log')
    MAX_BYTES = config.get_int('logging.max_bytes', default=15728640)  # 15MB
    BACKUP_COUNT = config.get_int('logging.backup_count', default=10)

    LOGGING['handlers']['file'] = {
        'level': LOG_LEVEL,
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': f'{LOG_DIR}/{APP_LOG_FILE}',
        'maxBytes': MAX_BYTES,
        'backupCount': BACKUP_COUNT,
        'formatter': 'verbose',
    }
    LOGGING['handlers']['error_file'] = {
        'level': 'ERROR',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': f'{LOG_DIR}/{ERROR_LOG_FILE}',
        'maxBytes': MAX_BYTES,
        'backupCount': BACKUP_COUNT,
        'formatter': 'verbose',
    }

    # Add file handlers to loggers
    LOGGING['root']['handlers'].append('file')
    LOGGING['loggers']['django']['handlers'].extend(['file', 'error_file'])
    LOGGING['loggers']['django.request']['handlers'].append('error_file')
    LOGGING['loggers']['django.security']['handlers'].append('error_file')
    LOGGING['loggers']['api']['handlers'].extend(['file', 'error_file'])
    LOGGING['loggers']['celery']['handlers'].extend(['file', 'error_file'])

# ============================================
# Sentry Configuration (Optional)
# ============================================

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=config.get_float('monitoring.sentry_traces_sample_rate', default=0.1),
            send_default_pii=config.get_bool('monitoring.sentry_send_pii', default=False),
            environment=ENVIRONMENT,
        )
    except ImportError:
        pass  # Sentry SDK not installed
