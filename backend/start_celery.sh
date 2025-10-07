#!/bin/bash
set -e

echo "========================================="
echo "Starting Celery Worker with Debug Info"
echo "========================================="

# Print environment info
echo "📍 Environment Variables:"
echo "  DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-not set}"
echo "  DB_HOST=${DB_HOST:-not set}"
echo "  REDIS_HOST=${REDIS_HOST:-not set}"
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

# Test Redis connection
echo ""
echo "🔍 Testing Redis connection..."
python -c "
import redis
import os

redis_host = os.environ.get('REDIS_HOST', 'redis')
try:
    r = redis.Redis(host=redis_host, port=6379, db=0)
    r.ping()
    print(f'  ✅ Redis connection successful to {redis_host}:6379')
except Exception as e:
    print(f'  ❌ Failed to connect to Redis: {e}')
    exit(1)
"

# Start Celery Worker
echo ""
echo "========================================="
echo "🚀 Starting Celery Worker"
echo "========================================="
echo "Command: celery -A config worker --loglevel=INFO --concurrency=1 --pool=threads"
echo ""

# Run celery with explicit settings
export DJANGO_SETTINGS_MODULE=config.settings
exec celery -A config worker --loglevel=INFO --concurrency=1 --pool=threads