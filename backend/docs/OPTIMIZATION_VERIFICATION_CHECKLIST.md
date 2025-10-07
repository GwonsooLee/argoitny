# Celery Optimization Verification Checklist

Use this checklist to verify that all optimizations are working correctly after deployment.

## Pre-Deployment Verification

### Code Review
- [x] All tasks use `only()` for minimal field loading
- [x] All tasks use `select_related()` or `prefetch_related()` where appropriate
- [x] All tasks use `bulk_create()` or `bulk_update()` for batch operations
- [x] All tasks use `update_fields` for targeted updates
- [x] All tasks have proper error handling and logging
- [x] All tasks have retry configuration with backoff
- [x] All tasks have time limits configured
- [x] Task routing is configured in settings
- [x] Queue priorities are set appropriately

### Configuration Review
- [x] `CELERY_TASK_ACKS_LATE = True`
- [x] `CELERY_TASK_REJECT_ON_WORKER_LOST = True`
- [x] `CELERY_WORKER_PREFETCH_MULTIPLIER = 4`
- [x] `CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000`
- [x] `CELERY_RESULT_COMPRESSION = 'gzip'`
- [x] `CELERY_RESULT_EXPIRES = 86400`
- [x] Task routes configured for all tasks
- [x] Redis connection settings correct
- [x] Cache configuration is correct

## Post-Deployment Verification

### Functional Testing

#### 1. execute_code_task
```bash
# Test code execution task
python manage.py shell
>>> from api.tasks import execute_code_task
>>> from api.models import Problem
>>> problem = Problem.objects.first()
>>> result = execute_code_task.delay('print("test")', 'python', problem.id, None, 'test@test.com', False)
>>> result.get()  # Should return execution results
```

**Verify:**
- [ ] Task completes successfully
- [ ] Results are saved to SearchHistory
- [ ] Problem metadata is updated
- [ ] Test results are correct
- [ ] Database queries < 5 (check with DEBUG=True)

#### 2. generate_script_task
```bash
# Test script generation task
>>> from api.tasks import generate_script_task
>>> from api.models import ScriptGenerationJob
>>> job = ScriptGenerationJob.objects.create(
...     platform='baekjoon',
...     problem_id='1000',
...     title='A+B',
...     language='python',
...     constraints='1 ≤ A, B ≤ 10'
... )
>>> result = generate_script_task.delay(job.id)
>>> result.get()
```

**Verify:**
- [ ] Task completes successfully
- [ ] Generator code is created
- [ ] Test cases are created with bulk_create
- [ ] No duplicate processing occurs
- [ ] Database queries < 5

#### 3. generate_outputs_task
```bash
# Test output generation task
>>> from api.tasks import generate_outputs_task
>>> result = generate_outputs_task.delay('baekjoon', '1000')
>>> result.get()
```

**Verify:**
- [ ] Task completes successfully
- [ ] Outputs are generated
- [ ] Bulk update is used
- [ ] Database queries < 5

#### 4. generate_hints_task
```bash
# Test hints generation task
>>> from api.tasks import generate_hints_task
>>> from api.models import SearchHistory
>>> history = SearchHistory.objects.filter(failed_count__gt=0).first()
>>> result = generate_hints_task.delay(history.id)
>>> result.get()
```

**Verify:**
- [ ] Task completes successfully
- [ ] Hints are generated and saved
- [ ] No duplicate hint generation
- [ ] Database queries = 1

#### 5. extract_problem_info_task
```bash
# Test problem info extraction task
>>> from api.tasks import extract_problem_info_task
>>> result = extract_problem_info_task.delay('https://www.acmicpc.net/problem/1000')
>>> result.get()
```

**Verify:**
- [ ] Task completes successfully
- [ ] Problem info is extracted
- [ ] Result is cached
- [ ] Second call uses cache (faster)

#### 6. Cache Warming Tasks
```bash
# Test cache warming
>>> from api.tasks import warm_problem_cache_task, warm_user_stats_cache_task
>>> result = warm_problem_cache_task.delay()
>>> result.get()
>>> result = warm_user_stats_cache_task.delay()
>>> result.get()
```

**Verify:**
- [ ] Problem cache is populated
- [ ] User stats cache is populated
- [ ] Cache entries exist in Redis
- [ ] Cache TTL is correct

### Performance Testing

#### Database Query Count
```python
from django.test.utils import override_settings
from django.db import connection, reset_queries

@override_settings(DEBUG=True)
def test_query_count():
    reset_queries()
    # Run task
    execute_code_task.apply(args=(...))
    print(f"Query count: {len(connection.queries)}")
    # Should be < 5
```

**Verify:**
- [ ] execute_code_task: < 5 queries
- [ ] generate_script_task: < 5 queries
- [ ] generate_outputs_task: < 5 queries
- [ ] generate_hints_task: < 3 queries
- [ ] extract_problem_info_task: < 3 queries

#### Cache Verification
```bash
# Check cache is working
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test_key', 'test_value', 300)
>>> cache.get('test_key')  # Should return 'test_value'
>>> cache.delete('test_key')
```

**Verify:**
- [ ] Cache set works
- [ ] Cache get works
- [ ] Cache delete works
- [ ] Cache TTL is respected

#### Worker Monitoring
```bash
# Check worker stats
celery -A config inspect stats
```

**Verify:**
- [ ] Workers are running
- [ ] All queues are being processed
- [ ] Task prefetch is working
- [ ] Memory usage is reasonable

### Load Testing

#### Concurrent Task Execution
```python
# Test concurrent execution
from api.tasks import execute_code_task
from api.models import Problem

problem = Problem.objects.first()
results = []
for i in range(50):
    result = execute_code_task.delay(
        'print("test")', 'python', problem.id,
        None, f'test{i}@test.com', False
    )
    results.append(result)

# Wait for all
for r in results:
    r.get()
```

**Verify:**
- [ ] All 50 tasks complete successfully
- [ ] No tasks are lost
- [ ] Database is not overwhelmed
- [ ] Workers handle load well

#### Queue Length Monitoring
```bash
# Monitor queue lengths
celery -A config inspect active_queues
```

**Verify:**
- [ ] Tasks are distributed across queues
- [ ] High-priority tasks execute first
- [ ] Queue lengths are reasonable

### Error Handling Testing

#### Retry Logic
```python
# Test retry with temporary failure
# (Mock a service to fail temporarily)
```

**Verify:**
- [ ] Tasks retry on failure
- [ ] Exponential backoff works
- [ ] Max retries is respected
- [ ] Failed tasks are logged

#### Worker Crash Recovery
```bash
# Kill a worker while processing tasks
kill -9 <worker_pid>
# Start new worker
celery -A config worker -Q execution -c 8
```

**Verify:**
- [ ] Tasks are requeued
- [ ] No tasks are lost
- [ ] System recovers gracefully

### Monitoring Verification

#### Logging
```bash
# Check logs for optimization markers
tail -f celery_worker.log | grep "OPTIMIZATION"
```

**Verify:**
- [ ] Structured logging is working
- [ ] Query counts are logged
- [ ] Errors are logged with context
- [ ] Log volume is reasonable

#### Metrics
```bash
# Check Celery metrics
celery -A config events
```

**Verify:**
- [ ] Task events are sent
- [ ] Task timing is tracked
- [ ] Success/failure counts are tracked

## Performance Benchmarking

### Before vs After Comparison

Create a benchmark script:
```python
import time
from django.db import connection, reset_queries
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def benchmark_task(task_func, *args, **kwargs):
    reset_queries()
    start = time.time()
    result = task_func.apply(args=args, kwargs=kwargs)
    end = time.time()

    print(f"Execution time: {end - start:.2f}s")
    print(f"Query count: {len(connection.queries)}")
    print(f"Result: {result.result}")
    return result
```

**Run benchmarks for:**
- [ ] execute_code_task
- [ ] generate_script_task
- [ ] generate_outputs_task
- [ ] generate_hints_task
- [ ] extract_problem_info_task

**Compare with baseline:**
- [ ] Execution time improved
- [ ] Query count reduced
- [ ] Memory usage reduced

## Production Verification

### Health Checks

#### Redis Connection
```bash
redis-cli ping  # Should return PONG
```
**Verify:** [ ] Redis is healthy

#### Database Connection
```bash
python manage.py dbshell
\l  # List databases
\q  # Quit
```
**Verify:** [ ] Database is healthy

#### Celery Workers
```bash
celery -A config inspect ping
```
**Verify:** [ ] All workers respond

### Traffic Monitoring

#### Task Throughput
```bash
# Monitor task completion rate
celery -A config inspect stats
```

**Verify:**
- [ ] Tasks/second is acceptable
- [ ] No significant backlog
- [ ] All queues are processing

#### Response Times
**Verify:**
- [ ] P50 latency improved
- [ ] P95 latency improved
- [ ] P99 latency improved

### Cost Verification

#### Database I/O
**Check RDS CloudWatch metrics:**
- [ ] Read IOPS reduced
- [ ] Write IOPS reduced
- [ ] Connection count stable

#### Memory Usage
**Check EC2 CloudWatch metrics:**
- [ ] Memory usage reduced
- [ ] CPU usage stable or reduced

#### API Costs
**Check Gemini API usage:**
- [ ] API call count reduced
- [ ] Cache hit rate > 60%

## Rollback Plan

If issues are detected:

1. **Immediate Rollback**
   ```bash
   git revert <commit_hash>
   git push
   # Redeploy previous version
   ```

2. **Partial Rollback**
   - Revert individual task optimizations
   - Keep configuration changes
   - Monitor for improvement

3. **Investigation**
   - Check error logs
   - Review metrics
   - Identify root cause

## Sign-off

### Development Team
- [ ] Code review completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Staging deployment successful

### QA Team
- [ ] Functional tests passed
- [ ] Performance tests passed
- [ ] Load tests passed
- [ ] No critical issues found

### DevOps Team
- [ ] Infrastructure ready
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Rollback plan tested

### Product Team
- [ ] User acceptance testing passed
- [ ] No impact on user experience
- [ ] Performance improvements confirmed

---

**Verification Date:** _____________
**Verified By:** _____________
**Status:** [ ] PASS  [ ] FAIL
**Notes:** _____________________________________________

---

## Quick Verification Script

Save this as `verify_optimizations.py`:

```python
#!/usr/bin/env python
"""Quick verification script for Celery optimizations"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection, reset_queries
from django.test.utils import override_settings
from django.core.cache import cache
from api.tasks import (
    execute_code_task,
    generate_script_task,
    generate_outputs_task,
    generate_hints_task,
    extract_problem_info_task,
)
from api.models import Problem, ScriptGenerationJob, SearchHistory

def test_cache():
    """Test cache functionality"""
    print("\n=== Testing Cache ===")
    cache.set('test_key', 'test_value', 300)
    value = cache.get('test_key')
    assert value == 'test_value', "Cache test failed"
    cache.delete('test_key')
    print("✓ Cache is working")

@override_settings(DEBUG=True)
def test_query_counts():
    """Test database query counts"""
    print("\n=== Testing Query Counts ===")

    problem = Problem.objects.first()
    if not problem:
        print("⚠ No problems found, skipping query count tests")
        return

    # Test execute_code_task
    reset_queries()
    result = execute_code_task.apply(
        args=('print("test")', 'python', problem.id, None, 'test@test.com', False)
    )
    query_count = len(connection.queries)
    print(f"execute_code_task: {query_count} queries", end="")
    if query_count <= 5:
        print(" ✓")
    else:
        print(f" ✗ (expected ≤ 5)")

    # Add more task tests here...

def test_worker_connectivity():
    """Test Celery worker connectivity"""
    print("\n=== Testing Worker Connectivity ===")
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        active = inspect.active()
        if active:
            print(f"✓ {len(active)} workers active")
        else:
            print("⚠ No active workers found")
    except Exception as e:
        print(f"✗ Worker connectivity test failed: {e}")

def main():
    print("=" * 60)
    print("Celery Optimization Verification")
    print("=" * 60)

    test_cache()
    test_worker_connectivity()
    test_query_counts()

    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
```

Run with:
```bash
python verify_optimizations.py
```
