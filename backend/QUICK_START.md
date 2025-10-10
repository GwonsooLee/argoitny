# ASGI Quick Start Guide

## TL;DR - Get Running in 5 Minutes

### 1. Install Dependencies (1 min)
```bash
cd /Users/gwonsoolee/algoitny/backend
pip install -r requirements.txt
```

### 2. Start ASGI Server (30 sec)
```bash
# Recommended: Uvicorn
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload
```

### 3. Test (30 sec)
```bash
# In another terminal
curl http://localhost:8000/api/health/
# Should return: {"status": "healthy"}
```

### 4. That's It!
Your Django app now runs on ASGI. Keep reading for details.

---

## Commands Cheat Sheet

### Start Servers

```bash
# ASGI (Recommended - Better Performance)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload

# ASGI Production (4 workers)
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4

# Alternative: Daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# WSGI (Old Way - Still Works)
python manage.py runserver 0.0.0.0:8000

# Celery (No changes needed)
celery -A config worker -l info
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/api/health/

# Problem list
curl http://localhost:8000/api/problems/

# Get specific problem (requires admin auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/problems/codeforces/1A/
```

---

## File Locations

### Core Files
- **ASGI Config**: `/Users/gwonsoolee/algoitny/backend/config/asgi.py`
- **Settings**: `/Users/gwonsoolee/algoitny/backend/config/settings.py`
- **Requirements**: `/Users/gwonsoolee/algoitny/backend/requirements.txt`

### Async Components
- **DynamoDB**: `/Users/gwonsoolee/algoitny/backend/api/dynamodb/async_client.py`
- **Gemini Service**: `/Users/gwonsoolee/algoitny/backend/api/services/gemini_service_async.py`
- **OpenAI Service**: `/Users/gwonsoolee/algoitny/backend/api/services/openai_service_async.py`
- **Example Views**: `/Users/gwonsoolee/algoitny/backend/api/views/problems_async.py`

### Documentation
- **Migration Guide**: `/Users/gwonsoolee/algoitny/backend/ASGI_MIGRATION_GUIDE.md`
- **Testing Guide**: `/Users/gwonsoolee/algoitny/backend/ASGI_TESTING_GUIDE.md`
- **Summary**: `/Users/gwonsoolee/algoitny/backend/MIGRATION_SUMMARY.md`

---

## Code Examples

### Use Async DynamoDB

```python
from api.dynamodb.async_client import AsyncDynamoDBClient

async def get_problem(platform, problem_id):
    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table('algoitny_main')
        response = await table.get_item(
            Key={'PK': f'PROBLEM#{platform}#{problem_id}', 'SK': 'METADATA'}
        )
        return response.get('Item')
```

### Use Async Gemini Service

```python
from api.services.gemini_service_async import AsyncGeminiService

async def extract_problem(url):
    service = AsyncGeminiService()
    metadata = await service.extract_problem_metadata_from_url(url)
    return metadata
```

### Create Async View

```python
from rest_framework.views import APIView
from rest_framework.response import Response

class MyAsyncView(APIView):
    async def get(self, request):
        # Async database operation
        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table('algoitny_main')
            response = await table.scan(Limit=10)
            items = response.get('Items', [])

        return Response(items, status=200)
```

### Convert Sync to Async

```python
# BEFORE (Sync)
def my_function():
    result = requests.get('https://api.example.com')
    return result.json()

# AFTER (Async)
async def my_function():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com')
        return response.json()
```

### Wrap Sync Operations

```python
from asgiref.sync import sync_to_async
from django.core.cache import cache

# Wrap Django cache (sync-only)
async def get_from_cache(key):
    return await sync_to_async(cache.get)(key)

# Wrap user method (sync-only)
async def check_admin(user):
    return await sync_to_async(lambda: user.is_admin())()
```

---

## Migration Checklist

### Before Starting
- [ ] Backup your code
- [ ] Review ASGI_MIGRATION_GUIDE.md
- [ ] Check Python version (3.11+)
- [ ] Check Django version (5.0+)

### Installation
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify no import errors: `python -c "import uvicorn, httpx, aioboto3"`

### Testing
- [ ] Start ASGI server: `uvicorn config.asgi:application --reload`
- [ ] Test health endpoint: `curl http://localhost:8000/api/health/`
- [ ] Test existing endpoints (should all work)
- [ ] Check Celery still works

### Migration (Optional - Not Required)
- [ ] Choose one endpoint to migrate (e.g., `/api/problems/`)
- [ ] Create async version in `*_async.py` file
- [ ] Test async version
- [ ] Compare performance
- [ ] Repeat for other endpoints

---

## Troubleshooting

### Server Won't Start

```bash
# Check for import errors
python config/asgi.py

# Check port availability
lsof -i :8000

# Kill process if needed
kill -9 $(lsof -t -i :8000)
```

### Async Not Working

```python
# Make sure method is async def
class MyView(APIView):
    async def get(self, request):  # ← Must have 'async'
        ...
```

### DynamoDB Connection Error

```bash
# Check LocalStack is running
docker ps | grep localstack

# Start LocalStack if needed
docker-compose up -d localstack

# Check environment variables
echo $LOCALSTACK_URL  # Should be http://localhost:4566
```

### Performance Not Improved

**Check**:
1. Are you using async views? (`async def`)
2. Are database calls async? (`await table.get_item(...)`)
3. Are HTTP calls async? (`async with httpx.AsyncClient()`)
4. Are you using enough workers? (`--workers 4`)

---

## Performance Tips

### Optimize Workers

```bash
# For I/O-bound (recommended)
# Formula: workers = (2 * CPU cores) + 1
# Example: 4 cores → 9 workers
uvicorn config.asgi:application --workers 9

# For CPU-bound
# Formula: workers = CPU cores
uvicorn config.asgi:application --workers 4
```

### Connection Pooling

Already configured in `async_client.py`:
- Max connections: 50
- Retry: 3 attempts
- Timeout: 30s

### Monitor Performance

```bash
# Install monitoring tools
pip install django-silk  # For profiling

# Use htop or top to monitor
htop

# Check logs
tail -f /var/log/django/algoitny.log
```

---

## Common Patterns

### Pattern 1: Async View with DB

```python
class MyView(APIView):
    async def get(self, request):
        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table('algoitny_main')
            response = await table.scan()
            return Response(response.get('Items', []))
```

### Pattern 2: Async View with Service

```python
class MyView(APIView):
    async def post(self, request):
        service = AsyncGeminiService()
        result = await service.extract_problem_metadata_from_url(
            request.data['url']
        )
        return Response(result)
```

### Pattern 3: Async View with Cache

```python
from asgiref.sync import sync_to_async

class MyView(APIView):
    async def get(self, request):
        # Get from cache
        cached = await sync_to_async(cache.get)('key')
        if cached:
            return Response(cached)

        # Fetch from DB
        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table('algoitny_main')
            response = await table.scan()
            data = response.get('Items', [])

        # Set cache
        await sync_to_async(cache.set)('key', data, 300)
        return Response(data)
```

---

## Next Steps

1. **Start ASGI server**: `uvicorn config.asgi:application --reload`
2. **Test it works**: `curl http://localhost:8000/api/health/`
3. **Read full guide**: See ASGI_MIGRATION_GUIDE.md
4. **Migrate endpoints**: Start with `/api/problems/`
5. **Benchmark**: Use ASGI_TESTING_GUIDE.md

---

## Questions?

- **Full details**: Read ASGI_MIGRATION_GUIDE.md
- **Testing**: Read ASGI_TESTING_GUIDE.md
- **Summary**: Read MIGRATION_SUMMARY.md
- **Django docs**: https://docs.djangoproject.com/en/5.0/topics/async/

---

**Last Updated**: October 10, 2025
**Status**: Ready to Use ✅
