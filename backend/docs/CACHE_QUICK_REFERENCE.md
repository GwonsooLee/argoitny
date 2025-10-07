# Cache Quick Reference Guide

## Quick Start

### 1. Enable Redis Cache (Production)

Redis caching is now configurable via environment variable. Set in your `.env` file:

```bash
# Enable Redis cache (recommended for production)
ENABLE_REDIS_CACHE=true
```

**When ENABLE_REDIS_CACHE=true:**
- Uses Redis cache (requires `django-redis` package)
- High performance, persistent cache across workers
- Suitable for production environments

**When ENABLE_REDIS_CACHE=false (default):**
- Uses Django's local memory cache (LocMemCache)
- No external dependencies required
- Suitable for development or single-worker deployments

### 2. Use Cache in Views

```python
from django.core.cache import cache
from api.utils.cache import CacheKeyGenerator

# In your view
cache_key = CacheKeyGenerator.problem_list_key(platform='baekjoon')
cached_data = cache.get(cache_key)
if cached_data:
    return Response(cached_data)

# ... fetch from database ...
cache.set(cache_key, data, timeout=300)
```

### 3. Invalidate Cache

```python
from api.utils.cache import CacheInvalidator

# Invalidate specific problem
CacheInvalidator.invalidate_problem_caches(problem_id=123)

# Invalidate by pattern
CacheInvalidator.invalidate_pattern('problem_*')
```

### 4. Warm Cache

```python
from api.tasks import warm_problem_cache_task
warm_problem_cache_task.delay()
```

## Common Cache Keys

| Endpoint | Cache Key Pattern | TTL |
|----------|------------------|-----|
| Problem List | `problem_list:{platform}:{search}:page:{page}` | 5 min |
| Problem Detail | `problem_detail:id:{id}` | 10 min |
| User Stats | `user_stats:{user_id}` | 3 min |
| Drafts | `problem_drafts:all` | 1 min |
| Registered | `problem_registered:all` | 5 min |

## Cache Utilities

### CacheKeyGenerator

```python
from api.utils.cache import CacheKeyGenerator

# Generate cache keys
key = CacheKeyGenerator.problem_list_key(platform='baekjoon')
key = CacheKeyGenerator.problem_detail_key(problem_id=123)
key = CacheKeyGenerator.user_stats_key(user_id=456)
```

### Decorators

```python
from api.utils.cache import cache_response, cache_queryset, cache_method

# Cache API responses
@cache_response(timeout=300)
def get(self, request):
    pass

# Cache queryset
@cache_queryset(timeout=600, cache_key="problems")
def get_problems():
    return Problem.objects.all()

# Cache model methods
class Problem(models.Model):
    @cache_method(timeout=600, key_attr='id')
    def get_stats(self):
        pass
```

### Manual Caching

```python
from api.utils.cache import get_or_set_cache

# Get from cache or compute
data = get_or_set_cache(
    'my_key',
    lambda: expensive_operation(),
    timeout=600
)
```

## Celery Tasks

### Cache Warming

```python
# Warm problem cache
from api.tasks import warm_problem_cache_task
warm_problem_cache_task.delay()

# Warm user stats
from api.tasks import warm_user_stats_cache_task
warm_user_stats_cache_task.delay([1, 2, 3])  # specific users
```

### Cache Invalidation

```python
from api.tasks import invalidate_cache_task
invalidate_cache_task.delay('problem_*')
```

## Redis Commands

### Check Cache

```bash
# Connect to Redis
redis-cli

# List all keys
KEYS algoitny:*

# Get a specific key
GET algoitny:1:problem_list:all:none:page:1

# Check TTL
TTL algoitny:1:problem_detail:id:123

# Delete a key
DEL algoitny:1:user_stats:456

# Clear all keys (CAREFUL!)
FLUSHDB
```

### Monitor Cache

```bash
# Monitor all commands
redis-cli MONITOR

# Get cache stats
redis-cli INFO stats

# Check memory usage
redis-cli INFO memory
```

## Django Shell Commands

### Test Cache

```python
python manage.py shell

from django.core.cache import cache

# Set value
cache.set('test', 'value', 60)

# Get value
cache.get('test')  # Returns: 'value'

# Delete value
cache.delete('test')

# Clear all
cache.clear()
```

### Check Cache Stats

```python
from django_redis import get_redis_connection

redis_conn = get_redis_connection("default")

# Get all keys
keys = redis_conn.keys("algoitny:*")
print(f"Total keys: {len(keys)}")

# Get stats
info = redis_conn.info('stats')
hits = info.get('keyspace_hits', 0)
misses = info.get('keyspace_misses', 0)
hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
print(f"Hit rate: {hit_rate * 100:.2f}%")
```

## Environment Variables

```bash
# .env file

# Enable/disable Redis cache (true/false)
ENABLE_REDIS_CACHE=false  # Set to true for production

# Redis connection settings (only used when ENABLE_REDIS_CACHE=true)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Configuration Guide

**Development Environment:**
```bash
ENABLE_REDIS_CACHE=false
```
- Uses local memory cache
- No Redis installation required
- Perfect for local development

**Production Environment:**
```bash
ENABLE_REDIS_CACHE=true
REDIS_HOST=your-redis-host.amazonaws.com  # e.g., ElastiCache endpoint
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-secure-password
```
- Uses Redis cache
- Shared cache across all workers
- Better performance and consistency

## Troubleshooting

### Cache Not Working

1. **Check if Redis is enabled:**
   ```python
   # In Django shell
   from django.conf import settings
   print(f"Redis enabled: {settings.ENABLE_REDIS_CACHE}")
   print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
   ```

2. **If using Redis (ENABLE_REDIS_CACHE=true), check Redis is running:**
   ```bash
   redis-cli ping  # Should return PONG
   ```

3. **Test cache in Django shell:**
   ```python
   from django.core.cache import cache
   cache.set('test', 'value', 60)
   print(cache.get('test'))  # Should return 'value'
   ```

4. **Check logs for errors:**
   ```bash
   tail -f /var/log/django/algoitny.log | grep -i cache
   ```

5. **If switching from LocMemCache to Redis:**
   - Set `ENABLE_REDIS_CACHE=true` in `.env`
   - Install required package: `pip install django-redis`
   - Restart Django application

### Stale Data

1. Check if signals are registered
2. Manually invalidate:
   ```python
   from api.utils.cache import CacheInvalidator
   CacheInvalidator.invalidate_pattern('*')
   ```

### High Memory

1. Check Redis memory:
   ```bash
   redis-cli INFO memory
   ```

2. Reduce TTLs in settings.py
3. Configure maxmemory policy

## Best Practices

1. **Always use CacheKeyGenerator** for consistent keys
2. **Set appropriate TTLs** based on data change frequency
3. **Use signals for automatic invalidation** instead of manual
4. **Log cache operations** for debugging
5. **Monitor hit rates** and adjust TTLs accordingly
6. **Handle cache failures gracefully** (IGNORE_EXCEPTIONS=True)
7. **Don't cache user-specific data** with long TTLs
8. **Use cache warming** for frequently accessed data

## Performance Tips

1. **Cache expensive queries** (joins, aggregations)
2. **Use select_related/prefetch_related** before caching
3. **Compress large responses** (enabled by default)
4. **Monitor cache size** and evict if needed
5. **Use connection pooling** (already configured)
6. **Batch cache operations** when possible

## Common Patterns

### View Caching

```python
def get(self, request):
    cache_key = generate_cache_key(request)
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # Expensive operation
    data = serialize_data()
    cache.set(cache_key, data, timeout=300)
    return Response(data)
```

### Conditional Caching

```python
def get(self, request):
    # Only cache for anonymous users
    if not request.user.is_authenticated:
        cache_key = generate_cache_key(request)
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

    # ... rest of the logic
```

### Cache Warming

```python
# In Celery task
def warm_cache():
    data = fetch_expensive_data()
    cache.set('my_key', data, timeout=3600)
```

## Files Reference

- **Settings**: `/Users/gwonsoolee/algoitny/backend/config/settings.py`
- **Cache Utils**: `/Users/gwonsoolee/algoitny/backend/api/utils/cache.py`
- **Signals**: `/Users/gwonsoolee/algoitny/backend/api/signals.py`
- **Tasks**: `/Users/gwonsoolee/algoitny/backend/api/tasks.py`
- **Views**: `/Users/gwonsoolee/algoitny/backend/api/views/`

## Documentation

- **Full Strategy**: `CACHING_STRATEGY.md`
- **Implementation Summary**: `CACHING_IMPLEMENTATION_SUMMARY.md`
- **This Guide**: `CACHE_QUICK_REFERENCE.md`
