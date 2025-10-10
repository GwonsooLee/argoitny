# ASGI Migration Guide

## Overview

This guide documents the migration of the AlgoItny Django backend from WSGI (synchronous) to ASGI (asynchronous) architecture. The migration enables async/await patterns throughout the application, improving performance for I/O-bound operations.

## Migration Status: PARTIAL (Hybrid Approach)

The application now supports **both WSGI and ASGI** modes:
- **ASGI mode**: Recommended for production (better performance)
- **WSGI mode**: Still supported for compatibility

## What Changed

### 1. Dependencies Added

New async dependencies in `requirements.txt`:

```
# ASGI server and async dependencies
uvicorn[standard]>=0.25.0      # ASGI server (recommended)
daphne>=4.0.0                  # Alternative ASGI server
httpx>=0.25.0                  # Async HTTP client (replaces requests)
aiohttp>=3.9.0                 # Alternative async HTTP client
aioboto3>=12.0.0               # Async AWS SDK (for DynamoDB)
asgiref>=3.7.0                 # ASGI utilities
beautifulsoup4>=4.12.0         # HTML parsing (for services)
```

### 2. Configuration Files Updated

#### `/Users/gwonsoolee/algoitny/backend/config/asgi.py`
- Enhanced ASGI application configuration
- Supports Uvicorn, Daphne, and Hypercorn servers
- Ready for WebSocket support (commented out for future use)

#### `/Users/gwonsoolee/algoitny/backend/config/settings.py`
- Added `ASGI_APPLICATION` setting
- Added `ASYNC_MODE = True` for Django 4.1+ async support
- Kept `WSGI_APPLICATION` for backwards compatibility

### 3. New Async Components

#### Async DynamoDB Client
**File**: `/Users/gwonsoolee/algoitny/backend/api/dynamodb/async_client.py`

```python
# Usage example
from api.dynamodb.async_client import AsyncDynamoDBClient

async def get_problem():
    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table('algoitny_main')
        response = await table.get_item(Key={'PK': 'PROBLEM#...', 'SK': 'METADATA'})
        return response.get('Item')
```

**Key features**:
- Context manager pattern for resource management
- Supports both LocalStack and AWS
- Automatic configuration from environment variables
- Connection pooling and retry logic

#### Async Gemini Service
**File**: `/Users/gwonsoolee/algoitny/backend/api/services/gemini_service_async.py`

```python
# Usage example
from api.services.gemini_service_async import AsyncGeminiService

async def extract_problem():
    service = AsyncGeminiService()
    metadata = await service.extract_problem_metadata_from_url(
        problem_url='https://codeforces.com/problem/1234/A',
        difficulty_rating=1500
    )
    return metadata
```

**Key changes**:
- Uses `httpx.AsyncClient` instead of `requests` for HTTP calls
- All methods are `async def` with `await` for I/O operations
- Uses `asyncio.to_thread()` for sync Gemini SDK calls
- Maintains same API as sync version

#### Async OpenAI Service
**File**: `/Users/gwonsoolee/algoitny/backend/api/services/openai_service_async.py`

```python
# Usage example
from api.services.openai_service_async import AsyncOpenAIService

async def generate_solution():
    service = AsyncOpenAIService()
    solution = await service.generate_solution_for_problem(
        problem_metadata={'title': '...', 'constraints': '...', 'samples': [...]},
        difficulty_rating=2000
    )
    return solution['solution_code']
```

**Key changes**:
- Uses `AsyncOpenAI` client instead of sync `OpenAI` client
- All methods are `async def` with `await`
- Native async support from OpenAI SDK
- Uses `httpx` for webpage fetching

#### Async Views (Example)
**File**: `/Users/gwonsoolee/algoitny/backend/api/views/problems_async.py`

```python
# Usage example
from api.views.problems_async import AsyncProblemListView

class AsyncProblemListView(APIView):
    permission_classes = [AllowAny]

    async def get(self, request):
        # Async database operations
        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table('algoitny_main')
            response = await table.query(...)
            problems = response.get('Items', [])

        return Response(problems, status=200)
```

**Key changes**:
- Methods are `async def` instead of `def`
- Use `await` for async operations (database, cache, HTTP)
- Use `sync_to_async` for sync-only operations (Django cache, user methods)
- Maintains same API structure as sync views

#### ASGI-Compatible Middleware
**File**: `/Users/gwonsoolee/algoitny/backend/api/middleware/security_headers.py`

```python
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        # Sync path
        response = self.get_response(request)
        return self._add_security_headers(response)

    async def __acall__(self, request):
        # Async path
        response = await self.get_response(request)
        return self._add_security_headers(response)
```

**Key features**:
- Implements both `__call__` (sync) and `__acall__` (async) methods
- Automatically detects async context
- Works in both WSGI and ASGI modes

## How to Run

### ASGI Mode (Recommended)

#### Option 1: Uvicorn (Recommended)
```bash
# Development (with auto-reload)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

# Production (with workers)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

#### Option 2: Daphne
```bash
# Development
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Production (with systemd or supervisor)
daphne -b 0.0.0.0 -p 8000 -u /tmp/daphne.sock config.asgi:application
```

#### Option 3: Hypercorn
```bash
# Development
hypercorn config.asgi:application --bind 0.0.0.0:8000 --reload

# Production
hypercorn config.asgi:application --bind 0.0.0.0:8000 --workers 4
```

### WSGI Mode (Backwards Compatibility)

```bash
# Development
python manage.py runserver 0.0.0.0:8000

# Production (Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Migration Strategy

### Phased Approach (Recommended)

We implemented a **hybrid approach** where both sync and async code coexist:

**Phase 1 (DONE)**: Infrastructure
- ✅ Update dependencies
- ✅ Configure ASGI
- ✅ Create async DynamoDB client
- ✅ Update middleware for ASGI compatibility

**Phase 2 (DONE)**: Services
- ✅ Create async Gemini service (`gemini_service_async.py`)
- ✅ Create async OpenAI service (`openai_service_async.py`)
- ⚠️ Keep existing sync services for compatibility

**Phase 3 (IN PROGRESS)**: Views
- ✅ Create example async views (`problems_async.py`)
- ⚠️ Migrate views incrementally (start with high-traffic endpoints)
- ⚠️ Keep existing sync views during transition

**Phase 4 (TODO)**: Complete Migration
- ⬜ Migrate all views to async
- ⬜ Migrate all services to async
- ⬜ Remove sync versions
- ⬜ Update all imports to use async versions

### View Migration Pattern

To convert a sync view to async:

```python
# BEFORE (Sync)
class MyView(APIView):
    def get(self, request):
        problem_repo = ProblemRepository()
        problems = problem_repo.list_problems()
        return Response(problems)

# AFTER (Async)
class MyView(APIView):
    async def get(self, request):
        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table('algoitny_main')
            response = await table.scan()
            problems = response.get('Items', [])
        return Response(problems)
```

**Key steps**:
1. Change `def` to `async def`
2. Replace sync database operations with async operations
3. Use `await` for async calls
4. Use `sync_to_async` for sync-only operations (cache, user methods)

## Performance Benefits

### Expected Improvements

1. **I/O-Bound Operations**: 2-5x throughput improvement
   - Database queries (DynamoDB)
   - External API calls (Gemini, OpenAI)
   - HTTP requests (webpage fetching)

2. **Concurrency**: Handle more concurrent requests
   - WSGI: 1 request per worker
   - ASGI: 100s of requests per worker (for I/O-bound ops)

3. **Resource Efficiency**:
   - Lower memory usage per request
   - Better CPU utilization
   - Faster response times under load

### Benchmarking (TODO)

To measure performance improvements:

```bash
# Benchmark sync endpoint
ab -n 1000 -c 10 http://localhost:8000/api/problems/

# Benchmark async endpoint
ab -n 1000 -c 10 http://localhost:8000/api/async/problems/
```

## Testing

### Unit Tests

Test both sync and async versions:

```python
# Test async views
import pytest
from asgiref.sync import async_to_sync

@pytest.mark.asyncio
async def test_async_problem_list():
    from api.views.problems_async import AsyncProblemListView

    view = AsyncProblemListView()
    request = factory.get('/api/problems/')
    response = await view.get(request)

    assert response.status_code == 200
```

### Integration Tests

1. **ASGI Server Test**:
   ```bash
   # Start server
   uvicorn config.asgi:application --port 8000

   # Test endpoint
   curl http://localhost:8000/api/health/
   ```

2. **Async Database Test**:
   ```bash
   # Test DynamoDB async operations
   python -c "import asyncio; from api.dynamodb.async_client import AsyncDynamoDBClient; asyncio.run(test())"
   ```

## Potential Issues & Solutions

### Issue 1: Sync Operations in Async Context

**Problem**: Calling sync functions in async views blocks the event loop.

**Solution**: Use `sync_to_async`:

```python
from asgiref.sync import sync_to_async

# Wrap sync function
async def my_view(request):
    # Wrong: cache.get('key')  # Blocks event loop
    # Correct:
    result = await sync_to_async(cache.get)('key')
```

### Issue 2: Django ORM in Async

**Problem**: Django ORM is sync-only.

**Solution**: Since we use DynamoDB (not ORM), this isn't an issue. For Django models (e.g., `SubscriptionPlan`), use:

```python
from asgiref.sync import sync_to_async
from api.models import SubscriptionPlan

# Wrap ORM queries
async def get_plan():
    plans = await sync_to_async(list)(SubscriptionPlan.objects.all())
    return plans
```

### Issue 3: Celery Task Dispatch

**Problem**: Celery task dispatch is sync.

**Solution**: Use `sync_to_async`:

```python
from asgiref.sync import sync_to_async

async def trigger_task():
    await sync_to_async(my_task.apply_async)({'arg': 'value'})
```

### Issue 4: Cache Operations

**Problem**: Django cache is sync-only.

**Solution**: Use `sync_to_async` or Redis async client:

```python
from asgiref.sync import sync_to_async
from django.core.cache import cache

# Option 1: Wrap Django cache
async def get_from_cache(key):
    return await sync_to_async(cache.get)(key)

# Option 2: Use Redis directly (requires aioredis)
import aioredis
redis = await aioredis.create_redis_pool('redis://localhost')
value = await redis.get('key')
```

## Celery Integration

Celery worker **remains synchronous** and works fine with ASGI:

```bash
# Start Celery worker (no changes needed)
celery -A config worker -l info --queues=default,generation,execution
```

**Note**: Celery tasks are triggered from async views using `sync_to_async`, but execute synchronously in workers.

## Deployment Recommendations

### Docker

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Use Uvicorn for ASGI
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Systemd

```ini
# /etc/systemd/system/algoitny-asgi.service
[Unit]
Description=AlgoItny ASGI Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/algoitny/backend
ExecStart=/usr/local/bin/uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: algoitny-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: algoitny-backend:latest
        command: ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
        ports:
        - containerPort: 8000
        env:
        - name: DJANGO_SETTINGS_MODULE
          value: "config.settings"
```

## Performance Tuning

### Uvicorn Workers

```bash
# CPU-bound: workers = CPU cores
uvicorn config.asgi:application --workers 4

# I/O-bound: workers = 2 * CPU cores + 1
uvicorn config.asgi:application --workers 9  # For 4-core machine
```

### Connection Pooling

DynamoDB connection pooling is automatic with aioboto3, but you can tune:

```python
# In async_client.py
config = Config(
    max_pool_connections=50,  # Increase for high concurrency
    retries={'max_attempts': 3, 'mode': 'standard'}
)
```

### Timeouts

Set appropriate timeouts:

```python
# HTTP client timeouts
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)

# DynamoDB timeouts
config = Config(
    read_timeout=30,
    connect_timeout=10
)
```

## Monitoring

### Metrics to Track

1. **Request latency**: p50, p95, p99
2. **Throughput**: requests/second
3. **Error rate**: % of failed requests
4. **Async task completion time**: DynamoDB queries, API calls
5. **Memory usage**: per worker
6. **CPU usage**: should remain low for I/O-bound ops

### Logging

Async operations are logged with standard Python logging:

```python
import logging
logger = logging.getLogger(__name__)

async def my_view(request):
    logger.info("Processing async request")
    # ... async operations ...
```

## Next Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Test ASGI server**:
   ```bash
   uvicorn config.asgi:application --reload
   ```

3. **Migrate high-traffic views** to async (start with `/api/problems/`)

4. **Benchmark performance** (compare WSGI vs ASGI)

5. **Gradually migrate remaining views** to async

6. **Remove sync versions** once migration is complete

## Additional Resources

- [Django Async Documentation](https://docs.djangoproject.com/en/5.0/topics/async/)
- [ASGI Specification](https://asgi.readthedocs.io/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [aioboto3 Documentation](https://aioboto3.readthedocs.io/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Django REST Framework Async Views](https://www.django-rest-framework.org/api-guide/views/#async-views)

## Support

For issues or questions about the migration:
1. Check this guide first
2. Review async example files (`*_async.py`)
3. Test with the example async views
4. Consult Django async documentation

---

**Migration Date**: 2025-10-10
**Django Version**: 5.0+
**Python Version**: 3.11+
**Status**: Partial (Hybrid WSGI/ASGI)
