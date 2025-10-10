#!/bin/bash
set -e

echo "========================================="
echo "Starting Celery Worker with Debug Info"
echo "========================================="

# Print environment info
echo "📍 Environment Variables:"
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-not set}"
echo "  DB_HOST=${DB_HOST:-not set}"
echo "  LOCALSTACK_URL=${LOCALSTACK_URL:-not set}"
echo "  DB_NAME=${DB_NAME:-not set}"

# Set Django settings module if not set
if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
    export DJANGO_SETTINGS_MODULE=config.settings
    echo "✅ Set DJANGO_SETTINGS_MODULE=config.settings"
fi

# Test Django settings loading
echo ""
echo "🔍 Testing Django settings loading..."
python -c "
import os
print(f'  Python path: {os.sys.path}')
print(f'  Current directory: {os.getcwd()}')
print(f'  DJANGO_SETTINGS_MODULE: {os.environ.get(\"DJANGO_SETTINGS_MODULE\")}')

try:
    from django.conf import settings
    import django
    django.setup()
    print('  ✅ Django settings loaded successfully')
    print(f'  ✅ CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}')
    print(f'  ✅ CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}')
except Exception as e:
    print(f'  ❌ Failed to load Django settings: {e}')
    exit(1)
"

# Test Celery import and configuration
echo ""
echo "🔍 Testing Celery configuration..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

try:
    from celery import Celery
    app = Celery('config')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    print('  ✅ Celery app configured successfully')

    # Test debug task only (no autodiscovery)
    from config.celery import debug_task
    print(f'  ✅ debug_task registered: {debug_task.name}')

    # API tasks can be registered explicitly when needed
    print('  ✅ Autodiscovery disabled - tasks must be explicitly imported')

except Exception as e:
    print(f'  ❌ Failed to configure Celery: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

# Test LocalStack SQS connection (only in development)
ENVIRONMENT=${ENVIRONMENT:-development}
if [ "$ENVIRONMENT" != "production" ]; then
    echo ""
    echo "🔍 Testing LocalStack SQS connection..."
    python -c "
import os
import boto3

localstack_url = os.environ.get('LOCALSTACK_URL', 'http://localstack:4566')
try:
    sqs = boto3.client(
        'sqs',
        endpoint_url=localstack_url,
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    # Try to list queues to test connection
    sqs.list_queues()
    print(f'  ✅ LocalStack SQS connection successful to {localstack_url}')
except Exception as e:
    print(f'  ⚠️ Could not connect to LocalStack SQS: {e}')
    print('  ⚠️ Continuing anyway - queues will be created on first use')
"
else
    echo ""
    echo "🚀 Production environment - using AWS SQS (no LocalStack)"
fi

# Start Celery Worker
echo ""
echo "========================================="
echo "🚀 Starting Celery Worker"
echo "========================================="
echo "Command: celery -A config worker --loglevel=INFO --concurrency=4 --pool=threads --prefetch-multiplier=1 --queues=jobs,celery,ai,generation,execution,maintenance"
echo ""

# Run celery with explicit settings and all queues
# --prefetch-multiplier=1: Each worker prefetches only 1 task at a time
# With 4 workers, total prefetch = 4 (not 16)
export DJANGO_SETTINGS_MODULE=config.settings
exec celery -A config worker --loglevel=INFO --concurrency=4 --pool=threads --prefetch-multiplier=1 --queues=jobs,celery,ai,generation,execution,maintenance