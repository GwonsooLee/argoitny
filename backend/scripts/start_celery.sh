#!/bin/bash
set -e

echo "========================================="
echo "Starting Celery Worker with Debug Info"
echo "========================================="

# Print environment info
echo "📍 Environment Variables:"
echo "  ENVIRONMENT=${ENVIRONMENT:-not set}"
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-not set}"
echo "  AWS_REGION=${AWS_REGION:-not set}"
echo "  AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-not set}"
echo "  LOCALSTACK_URL=${LOCALSTACK_URL:-not set}"

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
print(f'  ENVIRONMENT: {os.environ.get(\"ENVIRONMENT\", \"NOT SET\")}')
print(f'  DJANGO_SETTINGS_MODULE: {os.environ.get(\"DJANGO_SETTINGS_MODULE\")}')
print(f'  AWS_REGION: {os.environ.get(\"AWS_REGION\", \"NOT SET\")}')

try:
    from django.conf import settings
    import django
    django.setup()
    print('  ✅ Django settings loaded successfully')
    print(f'  ✅ ENVIRONMENT (in settings): {settings.ENVIRONMENT}')
    print(f'  ✅ IS_PRODUCTION: {settings.IS_PRODUCTION}')
    print(f'  ✅ CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}')
    print(f'  ✅ CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}')
except Exception as e:
    print(f'  ❌ Failed to load Django settings: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

# Test Celery import and configuration
echo ""
echo "🔍 Testing Celery configuration..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

print(f'  📍 ENVIRONMENT in celery.py context: {os.getenv(\"ENVIRONMENT\", \"NOT_SET\")}')

import django
django.setup()

try:
    from celery import Celery
    app = Celery('config')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    print('  ✅ Celery app configured successfully')

    # Check broker URL
    print(f'  ✅ Broker URL: {app.conf.broker_url}')
    print(f'  ✅ Broker Transport Options: {app.conf.broker_transport_options}')

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

# Final environment check before starting celery
echo "🔍 Final Environment Check:"
echo "  ENVIRONMENT=${ENVIRONMENT:-NOT_SET}"
echo "  AWS_REGION=${AWS_REGION:-NOT_SET}"
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-NOT_SET}"
echo ""

# Check actual broker configuration that will be used
echo "🔍 Checking actual Celery broker configuration..."
python -c "
from config.celery import app
print(f'  Broker URL: {app.conf.broker_url}')
print(f'  Broker Transport Options:')
for key, value in app.conf.broker_transport_options.items():
    print(f'    {key}: {value}')
" || echo "  ⚠️ Failed to load celery app config"
echo ""

# Run celery with explicit settings and all queues
# --prefetch-multiplier=1: Each worker prefetches only 1 task at a time
# With 4 workers, total prefetch = 4 (not 16)
export DJANGO_SETTINGS_MODULE=config.settings

echo "🎯 Executing celery command with DEBUG logging..."
set -x  # Enable command tracing
# Use DEBUG level to see connection errors
exec celery -A config worker --loglevel=DEBUG --concurrency=4 --pool=threads --prefetch-multiplier=1 --queues=jobs,celery,ai,generation,execution,maintenance