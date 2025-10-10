# ASGI Testing Guide

## Quick Start Testing

### 1. Install Dependencies

```bash
cd /Users/gwonsoolee/algoitny/backend
pip install -r requirements.txt
```

### 2. Start ASGI Server

```bash
# Option 1: Uvicorn (Recommended)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

# Option 2: Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Option 3: Keep using WSGI (for comparison)
python manage.py runserver 0.0.0.0:8000
```

### 3. Test Basic Endpoints

```bash
# Health check
curl http://localhost:8000/api/health/

# Problem list (sync version - still works)
curl http://localhost:8000/api/problems/

# If you've migrated specific endpoints, test them
curl http://localhost:8000/api/async/problems/  # Example async endpoint
```

## Testing Async Components

### Test Async DynamoDB Client

Create a test script `/Users/gwonsoolee/algoitny/backend/test_async_dynamodb.py`:

```python
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings before importing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from api.dynamodb.async_client import AsyncDynamoDBClient


async def test_async_dynamodb():
    """Test async DynamoDB client"""
    print("Testing async DynamoDB client...")

    try:
        # Test getting client
        async with AsyncDynamoDBClient.get_client() as client:
            print("✓ Async client created successfully")

            # Test listing tables
            response = await client.list_tables()
            tables = response.get('TableNames', [])
            print(f"✓ Found {len(tables)} tables: {tables}")

        # Test getting resource
        async with AsyncDynamoDBClient.get_resource() as resource:
            print("✓ Async resource created successfully")

            # Test table access
            table = await resource.Table(AsyncDynamoDBClient._table_name)
            print(f"✓ Table '{AsyncDynamoDBClient._table_name}' accessed successfully")

        print("\n✅ All async DynamoDB tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_async_dynamodb())
```

Run the test:
```bash
python test_async_dynamodb.py
```

### Test Async Services

Create a test script `/Users/gwonsoolee/algoitny/backend/test_async_services.py`:

```python
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from api.services.gemini_service_async import AsyncGeminiService
from api.services.openai_service_async import AsyncOpenAIService


async def test_gemini_service():
    """Test async Gemini service"""
    print("\n--- Testing Async Gemini Service ---")

    service = AsyncGeminiService()

    if not service.model:
        print("⚠️  Gemini API key not configured, skipping test")
        return

    try:
        # Test webpage fetching
        print("Testing webpage fetch...")
        url = "https://codeforces.com/problemset/problem/1/A"
        content = await service.fetch_webpage_async(url)
        print(f"✓ Fetched {len(content)} chars from {url}")

        # Test metadata extraction
        print("Testing metadata extraction...")
        metadata = await service.extract_problem_metadata_from_url(url)
        print(f"✓ Extracted problem: {metadata.get('title')}")
        print(f"✓ Platform: {metadata.get('platform')}, ID: {metadata.get('problem_id')}")
        print(f"✓ Samples: {len(metadata.get('samples', []))}")

        print("✅ Gemini service test passed!")

    except Exception as e:
        print(f"❌ Gemini service test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_openai_service():
    """Test async OpenAI service"""
    print("\n--- Testing Async OpenAI Service ---")

    service = AsyncOpenAIService()

    if not service.client:
        print("⚠️  OpenAI API key not configured, skipping test")
        return

    try:
        # Test webpage fetching
        print("Testing webpage fetch...")
        url = "https://codeforces.com/problemset/problem/1/A"
        content = await service.fetch_webpage_async(url)
        print(f"✓ Fetched {len(content)} chars from {url}")

        # Test metadata extraction
        print("Testing metadata extraction...")
        metadata = await service.extract_problem_metadata_from_url(url)
        print(f"✓ Extracted problem: {metadata.get('title')}")
        print(f"✓ Platform: {metadata.get('platform')}, ID: {metadata.get('problem_id')}")
        print(f"✓ Samples: {len(metadata.get('samples', []))}")

        print("✅ OpenAI service test passed!")

    except Exception as e:
        print(f"❌ OpenAI service test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_gemini_service()
    await test_openai_service()


if __name__ == '__main__':
    asyncio.run(main())
```

Run the test:
```bash
python test_async_services.py
```

## Performance Comparison

### Benchmark Script

Create `/Users/gwonsoolee/algoitny/backend/benchmark_async.py`:

```python
import asyncio
import time
import httpx
from statistics import mean, median


async def benchmark_endpoint(url, num_requests=100, concurrent=10):
    """Benchmark an endpoint with concurrent requests"""
    print(f"\nBenchmarking: {url}")
    print(f"Requests: {num_requests}, Concurrency: {concurrent}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        times = []
        start_time = time.time()

        # Create chunks of concurrent requests
        for i in range(0, num_requests, concurrent):
            chunk_size = min(concurrent, num_requests - i)
            tasks = []

            for _ in range(chunk_size):
                task = client.get(url)
                tasks.append(task)

            # Execute concurrent requests
            chunk_start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            chunk_time = time.time() - chunk_start

            # Record times
            for response in responses:
                if isinstance(response, Exception):
                    print(f"  Error: {response}")
                else:
                    times.append(chunk_time / chunk_size)

            print(f"  Completed {i + chunk_size}/{num_requests} requests")

        total_time = time.time() - start_time

        # Calculate statistics
        if times:
            print(f"\nResults:")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Requests/sec: {num_requests / total_time:.2f}")
            print(f"  Mean latency: {mean(times) * 1000:.2f}ms")
            print(f"  Median latency: {median(times) * 1000:.2f}ms")
            print(f"  Min latency: {min(times) * 1000:.2f}ms")
            print(f"  Max latency: {max(times) * 1000:.2f}ms")


async def main():
    base_url = "http://localhost:8000"

    # Test health endpoint
    await benchmark_endpoint(f"{base_url}/api/health/", num_requests=100, concurrent=10)

    # Test problem list
    await benchmark_endpoint(f"{base_url}/api/problems/", num_requests=50, concurrent=5)


if __name__ == '__main__':
    asyncio.run(main())
```

Run benchmarks:
```bash
# Start server first
uvicorn config.asgi:application --host 0.0.0.0 --port 8000

# In another terminal
python benchmark_async.py
```

## Unit Tests with Pytest

### Setup Pytest for Async

Install pytest-asyncio:
```bash
pip install pytest pytest-asyncio pytest-django
```

### Example Test File

Create `/Users/gwonsoolee/algoitny/backend/tests/test_async_views.py`:

```python
import pytest
from rest_framework.test import APIRequestFactory
from api.views.problems_async import AsyncProblemListView


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_async_problem_list_view():
    """Test async problem list view"""
    factory = APIRequestFactory()
    request = factory.get('/api/problems/')

    view = AsyncProblemListView()
    response = await view.get(request)

    assert response.status_code == 200
    assert isinstance(response.data, list)


@pytest.mark.asyncio
async def test_async_dynamodb_client():
    """Test async DynamoDB client"""
    from api.dynamodb.async_client import AsyncDynamoDBClient

    async with AsyncDynamoDBClient.get_client() as client:
        response = await client.list_tables()
        assert 'TableNames' in response
```

Run tests:
```bash
pytest tests/test_async_views.py -v
```

## Troubleshooting

### Common Issues

**Issue**: `RuntimeError: Event loop is closed`

**Solution**: Make sure to use `asyncio.run()` or proper event loop management:
```python
# Wrong
loop = asyncio.get_event_loop()
loop.run_until_complete(my_async_function())

# Correct
asyncio.run(my_async_function())
```

**Issue**: `SynchronousOnlyOperation: You cannot call this from an async context!`

**Solution**: Wrap sync operations with `sync_to_async`:
```python
from asgiref.sync import sync_to_async

# Wrap Django cache calls
result = await sync_to_async(cache.get)('key')
```

**Issue**: ASGI server won't start

**Solution**: Check for:
1. Import errors in `config/asgi.py`
2. Missing dependencies: `pip install -r requirements.txt`
3. Port already in use: `lsof -i :8000` and kill the process

**Issue**: Async view not working

**Solution**: Ensure:
1. Method is `async def`, not `def`
2. All I/O operations use `await`
3. View is registered in URL patterns correctly

## Next Steps

1. ✅ Test ASGI server startup
2. ✅ Test async DynamoDB client
3. ✅ Test async services (Gemini, OpenAI)
4. ⬜ Run benchmarks to compare WSGI vs ASGI
5. ⬜ Migrate one view at a time
6. ⬜ Add async unit tests
7. ⬜ Deploy to staging environment

## Monitoring in Production

### Metrics to Track

1. **Response Time**: Async should be faster for I/O-bound ops
2. **Throughput**: Requests/second should increase
3. **Memory Usage**: Should remain stable or decrease
4. **Error Rate**: Should remain unchanged

### Logging

Add detailed logging for async operations:

```python
import logging
logger = logging.getLogger(__name__)

async def my_async_function():
    logger.info("Starting async operation")
    start_time = time.time()

    # ... async operations ...

    duration = time.time() - start_time
    logger.info(f"Async operation completed in {duration:.2f}s")
```

---

**Testing Date**: 2025-10-10
**Status**: Ready for Testing
**Environment**: Development

For production deployment, see ASGI_MIGRATION_GUIDE.md
