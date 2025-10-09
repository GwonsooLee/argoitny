# Celery + SQS Configuration Guide

## ⚠️ CRITICAL UPDATE: Changed to `acks_late=False`

**As of latest update**, we have changed the Celery configuration from `acks_late=True` to `acks_late=False` to prevent duplicate task execution.

### Why the Change?

#### Previous Approach (acks_late=True)
- Messages were acknowledged only after task completion
- If task took longer than visibility timeout, SQS would make message visible again
- Another worker could pick up the same message, causing duplicates
- Required careful visibility timeout tuning

#### New Approach (acks_late=False) ✅
- **Messages are acknowledged immediately on consume**
- **Queue message is deleted right away, preventing any duplicates**
- Combined with DynamoDB atomic updates for idempotency
- More predictable behavior, no visibility timeout issues

## Critical Settings to Prevent Duplicate Task Execution

### Problem
When using Celery with SQS as the broker, tasks can be executed multiple times if not configured correctly. This happens because:

1. **SQS Visibility Timeout**: When a message is consumed from SQS, it becomes "invisible" for a certain period (visibility timeout)
2. **Task Execution Time**: If a task takes longer than the visibility timeout, SQS makes the message visible again
3. **Multiple Workers**: Another worker can pick up the same message, causing duplicate execution

### Solution (Updated)

#### 1. Immediate Acknowledgement (acks_late=False)
```python
# tasks.py
@shared_task(
    bind=True,
    acks_late=False,  # ACK immediately on consume - removes message from queue
    reject_on_worker_lost=True,
)
def my_task(self):
    # Task code
    pass
```

With `acks_late=False`:
- ✅ Message is acknowledged immediately when worker receives it
- ✅ Message is deleted from queue right away
- ✅ No other worker can pick up the same message
- ✅ No visibility timeout issues
- ⚠️ If worker crashes, task is lost (acceptable with DynamoDB idempotency)

#### 2. DynamoDB Atomic Updates for Idempotency
```python
# Atomic conditional update - only update if status is PENDING
success, job = job_repo.conditional_update_status_to_processing(
    job_id=job_id,
    celery_task_id=self.request.id,
    expected_status='PENDING'
)

if not success:
    # Another worker already claimed this job - skip
    logger.info(f"Job {job_id} already claimed by another worker")
    return {'status': 'SKIPPED'}
```

**DynamoDB ConditionExpression ensures**:
- Only one worker can update status from PENDING to PROCESSING
- Second worker's update fails atomically
- Prevents race conditions at database level

#### 3. Visibility Timeout (Safety Buffer)
```python
# settings.py
CELERY_TASK_TIME_LIMIT = 1800  # 30 minutes

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # 60 minutes (task_time_limit * 2)
}
```

With `acks_late=False`, visibility timeout is just a safety buffer:
- Messages are ACKed immediately, so timeout rarely matters
- Set to 2x task_time_limit for safety
- Protects against edge cases where ACK fails
```python
def extract_problem_info_task(self, job_id, ...):
    # 1. Atomic status check and update
    if not job_repo.claim_job(job_id):
        logger.warning(f"Job {job_id} already processing")
        return
    
    try:
        # 2. Do the work
        result = do_work()
        
        # 3. Update status
        job_repo.update_status(job_id, 'COMPLETED')
    except Exception as e:
        # 4. Handle errors
        job_repo.update_status(job_id, 'FAILED')
```

## Current Configuration (Updated)

### Task Time Limits
- `CELERY_TASK_TIME_LIMIT`: 1800s (30 minutes)
- `CELERY_TASK_SOFT_TIME_LIMIT`: 1680s (28 minutes)

### SQS Settings
- `visibility_timeout`: 3600s (60 minutes) - **increased for safety buffer**
- `polling_interval`: 1s

### Worker Settings
- `CELERY_WORKER_PREFETCH_MULTIPLIER`: 1 (prevents prefetching)
- `CELERY_TASK_ACKS_LATE`: **False** (immediate acknowledgement) ✅ **CHANGED**
- `CELERY_TASK_REJECT_ON_WORKER_LOST`: True

## Troubleshooting

### Symptom: Task executed multiple times (RARE with acks_late=False)
**Cause**: Race condition before atomic update

**Solution**: Ensure DynamoDB atomic updates are working
```python
# All tasks should use conditional_update_status_to_processing
success, job = job_repo.conditional_update_status_to_processing(
    job_id=job_id,
    celery_task_id=self.request.id,
    expected_status='PENDING'
)
```

### Symptom: Tasks lost after worker crash
**Cause**: `acks_late=False` means message is deleted immediately

**Solution**: This is expected behavior with acks_late=False
- DynamoDB job status remains PROCESSING
- Orphaned job recovery task will mark it as FAILED after timeout
- User can retry the job

### Symptom: "Job already claimed by another worker" messages
**Cause**: This is **NORMAL** behavior when multiple workers receive the same message

**Solution**: No action needed - this proves the system is working correctly
- Message was delivered to multiple workers (SQS at-least-once delivery)
- First worker ACKs and deletes the message
- Second worker's atomic update fails (job already PROCESSING)
- Logs show INFO level message (not an error)

### Symptom: High memory usage
**Cause**: Too many prefetched tasks

**Solution**: Set prefetch_multiplier to 1
```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

## Best Practices (Updated)

1. **Use acks_late=False**: Acknowledge messages immediately to prevent duplicates
2. **DynamoDB atomic updates**: Use conditional updates for all state changes
3. **Implement idempotent tasks**: Tasks should handle being called multiple times safely
4. **Monitor task duration**: Ensure tasks complete within time limits
5. **Set visibility timeout as safety buffer**: 2x task_time_limit recommended
6. **Implement orphaned job recovery**: Clean up jobs stuck in PROCESSING state

## Migration from acks_late=True to acks_late=False

If you're migrating from the old configuration:

### Step 1: Add Atomic Updates to All Tasks
```python
# Before
job = JobHelper.get_job(job_id)
if job['status'] == 'PROCESSING':
    return  # Race condition possible!
JobHelper.update_job(job_id, {'status': 'PROCESSING'})

# After
success, job = JobHelper.conditional_update_job_to_processing(
    job_id=job_id,
    celery_task_id=self.request.id,
    expected_status='PENDING'
)
if not success:
    return  # Already processing - safe!
```

### Step 2: Update Task Decorators
```python
# Before
@shared_task(acks_late=True)

# After
@shared_task(acks_late=False)
```

### Step 3: Update Settings
```python
# settings.py
CELERY_TASK_ACKS_LATE = False
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # Increase for safety
}
```

### Step 4: Deploy and Monitor
- Deploy changes to all workers
- Monitor logs for "already claimed" messages (INFO level - this is normal)
- Verify no duplicate task execution in DynamoDB job records

## References

- [Celery SQS Transport](https://docs.celeryq.dev/en/stable/userguide/configuration.html#broker-transport-options)
- [SQS Visibility Timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [Celery Task Execution](https://docs.celeryq.dev/en/stable/userguide/tasks.html#task-execution-options)
