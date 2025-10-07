# DynamoDB Schema Quick Reference

## Table Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AlgoItny-Main                                │
│  (Provisioned: 25-500 RCU, 10-100 WCU, Auto-scaling)               │
│                                                                      │
│  Entity Types: Problem, TestCase, SearchHistory, UsageLog, Job      │
│  GSIs: 3 (Entity+Time, Filter+Time, Tertiary+Time)                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       AlgoItny-Users                                │
│  (On-Demand)                                                        │
│                                                                      │
│  Entity Types: User                                                 │
│  GSIs: 3 (GoogleID, PlanMembership, UserID)                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       AlgoItny-Plans                                │
│  (On-Demand)                                                        │
│                                                                      │
│  Entity Types: SubscriptionPlan                                     │
│  GSIs: 1 (ActivePlans)                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Patterns

### 1. Problem + TestCases (Hierarchical Data)

```
┌─────────────────────────────────────────────────────────────────────┐
│ PK: PROBLEM#baekjoon#1000                                           │
├─────────────────────────────────────────────────────────────────────┤
│ SK: METADATA                         ← Problem entity               │
│ SK: TESTCASE#2025-01-15T10:30:00Z#1 ← Test case 1                  │
│ SK: TESTCASE#2025-01-15T10:30:00Z#2 ← Test case 2                  │
│ SK: TESTCASE#2025-01-15T10:30:00Z#3 ← Test case 3                  │
└─────────────────────────────────────────────────────────────────────┘

Query: Get problem with all test cases in ONE query
KeyCondition: PK = "PROBLEM#baekjoon#1000"
```

### 2. User's History Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ PK: USER#user-uuid-123                                              │
├─────────────────────────────────────────────────────────────────────┤
│ SK: HISTORY#2025-01-15T14:30:00Z#h1  ← Most recent                 │
│ SK: HISTORY#2025-01-15T10:00:00Z#h2                                │
│ SK: HISTORY#2025-01-14T18:45:00Z#h3                                │
│ SK: USAGE#2025-01-15#hint#14:30:00Z#u1                             │
│ SK: USAGE#2025-01-15#execution#10:00:00Z#u2                        │
└─────────────────────────────────────────────────────────────────────┘

Query: Get user's history ordered by time
KeyCondition: PK = "USER#user-uuid-123" AND begins_with(SK, "HISTORY#")
ScanIndexForward: False (descending)
```

### 3. Daily Usage Tracking

```
┌─────────────────────────────────────────────────────────────────────┐
│ PK: USER#user-uuid-123                                              │
├─────────────────────────────────────────────────────────────────────┤
│ SK: USAGE#2025-01-15#hint#14:30:00Z#u1                             │
│ SK: USAGE#2025-01-15#hint#14:35:00Z#u2                             │
│ SK: USAGE#2025-01-15#execution#10:00:00Z#u3                        │
│ SK: USAGE#2025-01-15#execution#10:05:00Z#u4                        │
└─────────────────────────────────────────────────────────────────────┘

Query: Count today's hints
KeyCondition: PK = "USER#user-uuid-123" AND begins_with(SK, "USAGE#2025-01-15#hint#")
Select: COUNT
```

---

## GSI Usage Guide

### AlgoItny-Main Table GSIs

#### GSI1: Entity Type + Time Index

```
┌──────────────────────────────┬──────────────────────────────┐
│ GSI1PK (Partition Key)       │ GSI1SK (Sort Key)            │
├──────────────────────────────┼──────────────────────────────┤
│ PLATFORM#baekjoon            │ 2025-01-15T10:30:00Z         │
│ PLATFORM#codeforces          │ 2025-01-15T10:30:00Z         │
│ PUBLIC#true                  │ 2025-01-15T14:30:00Z         │
│ JOBTYPE#script_generation    │ 2025-01-15T10:00:00Z         │
└──────────────────────────────┴──────────────────────────────┘
```

**Use Cases:**
- List problems by platform (ordered by time)
- Public history feed
- Jobs by type

**Example Query:**
```python
# Get all problems from Baekjoon, most recent first
response = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={':pk': 'PLATFORM#baekjoon'},
    ScanIndexForward=False
)
```

#### GSI2: Secondary Filter + Time Index

```
┌──────────────────────────────┬──────────────────────────────┐
│ GSI2PK (Partition Key)       │ GSI2SK (Sort Key)            │
├──────────────────────────────┼──────────────────────────────┤
│ COMPLETED#true               │ 2025-01-15T10:30:00Z         │
│ COMPLETED#false              │ 2025-01-15T10:30:00Z         │
│ PLATFORM#baekjoon            │ 2025-01-15T14:30:00Z         │
│ STATUS#PENDING               │ 2025-01-15T10:00:00Z         │
└──────────────────────────────┴──────────────────────────────┘
```

**Use Cases:**
- List completed problems (drafts)
- Filter history by platform
- Jobs by status

#### GSI3: Tertiary Filter + Time OR Lookup Index

```
┌──────────────────────────────┬──────────────────────────────┐
│ GSI3PK (Partition Key)       │ GSI3SK (Sort Key)            │
├──────────────────────────────┼──────────────────────────────┤
│ LANGUAGE#python              │ 2025-01-15T10:30:00Z         │
│ LANGUAGE#cpp                 │ 2025-01-15T10:30:00Z         │
│ TASK#celery-task-xyz         │ METADATA                     │
└──────────────────────────────┴──────────────────────────────┘
```

**Use Cases:**
- Filter problems/history by language
- Lookup job by Celery task ID

---

## Common Query Patterns

### Pattern 1: Get Single Item

```python
# By primary key (PK + SK)
response = table.get_item(
    Key={
        'PK': 'PROBLEM#baekjoon#1000',
        'SK': 'METADATA'
    }
)
problem = response['Item']
```

**Performance:** 1 RCU, <10ms latency

### Pattern 2: Get Item with Children

```python
# Get problem with all test cases
response = table.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={':pk': 'PROBLEM#baekjoon#1000'}
)

items = response['Items']
problem = next(item for item in items if item['SK'] == 'METADATA')
test_cases = [item for item in items if item['SK'].startswith('TESTCASE#')]
```

**Performance:** 1 query, RCU = (total_item_size / 4KB) rounded up

### Pattern 3: Query with Time Range

```python
# Get user's history from last 7 days
from datetime import datetime, timedelta

seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

response = table.query(
    KeyConditionExpression='PK = :pk AND SK >= :sk',
    ExpressionAttributeValues={
        ':pk': f'USER#{user_id}',
        ':sk': f'HISTORY#{seven_days_ago}'
    },
    ScanIndexForward=False
)
```

**Performance:** Efficient range query, paginated

### Pattern 4: GSI Query with Filter

```python
# Get completed Python problems
response = table.query(
    IndexName='GSI3',
    KeyConditionExpression='GSI3PK = :pk',
    FilterExpression='IsCompleted = :completed',
    ExpressionAttributeValues={
        ':pk': 'LANGUAGE#python',
        ':completed': True
    },
    ScanIndexForward=False
)
```

**Performance:** GSI query + post-filter, consumes RCUs for all scanned items

### Pattern 5: Count Without Reading Data

```python
# Count today's hints for rate limiting
today = datetime.utcnow().strftime('%Y-%m-%d')

response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': f'USER#{user_id}',
        ':sk': f'USAGE#{today}#hint#'
    },
    Select='COUNT'
)

count = response['Count']
```

**Performance:** Very efficient, minimal RCU consumption

### Pattern 6: Batch Write

```python
# Create problem with multiple test cases
with table.batch_writer() as batch:
    # Write problem
    batch.put_item(Item={
        'PK': 'PROBLEM#baekjoon#1000',
        'SK': 'METADATA',
        # ... problem attributes
    })

    # Write test cases
    for tc in test_cases:
        batch.put_item(Item={
            'PK': 'PROBLEM#baekjoon#1000',
            'SK': f'TESTCASE#{timestamp}#{tc.id}',
            # ... test case attributes
        })
```

**Performance:** Up to 25 items per batch, parallel writes

### Pattern 7: Update with Condition

```python
# Update job status only if currently PENDING
response = table.update_item(
    Key={'PK': 'JOB#job-123', 'SK': 'METADATA'},
    UpdateExpression='SET #status = :new_status, UpdatedAt = :time',
    ConditionExpression='#status = :old_status',
    ExpressionAttributeNames={'#status': 'Status'},
    ExpressionAttributeValues={
        ':new_status': 'PROCESSING',
        ':old_status': 'PENDING',
        ':time': datetime.utcnow().isoformat()
    }
)
```

**Performance:** Conditional update, prevents race conditions

---

## Key Anti-Patterns to Avoid

### 1. Don't Scan Without Pagination

```python
# BAD: Scans entire table
response = table.scan()  # Expensive and slow!

# GOOD: Query with pagination
response = table.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={':pk': 'USER#user-123'},
    Limit=20
)
```

### 2. Don't Use Multiple Queries When One Will Do

```python
# BAD: N+1 query problem
problem = table.get_item(Key={'PK': 'PROBLEM#baekjoon#1000', 'SK': 'METADATA'})
test_cases = []
for tc_id in problem['test_case_ids']:
    tc = table.get_item(Key={'PK': 'TESTCASE#' + tc_id, 'SK': 'METADATA'})
    test_cases.append(tc)

# GOOD: Single query with hierarchical data
response = table.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={':pk': 'PROBLEM#baekjoon#1000'}
)
```

### 3. Don't Create Hot Partitions

```python
# BAD: All usage logs share same PK
PK = 'USAGE_LOG'  # All users write to same partition!

# GOOD: Distribute by user
PK = f'USER#{user_id}'  # Each user has separate partition
```

### 4. Don't Fetch More Data Than Needed

```python
# BAD: Fetch entire item when you only need count
response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={':pk': 'USER#123', ':sk': 'HISTORY#'}
)
count = len(response['Items'])  # Wastes bandwidth!

# GOOD: Use COUNT
response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={':pk': 'USER#123', ':sk': 'HISTORY#'},
    Select='COUNT'
)
count = response['Count']
```

### 5. Don't Ignore Pagination Tokens

```python
# BAD: Only gets first page
response = table.query(...)
items = response['Items']  # Might be incomplete!

# GOOD: Handle pagination
items = []
last_key = None
while True:
    params = {'KeyConditionExpression': '...'}
    if last_key:
        params['ExclusiveStartKey'] = last_key

    response = table.query(**params)
    items.extend(response['Items'])

    last_key = response.get('LastEvaluatedKey')
    if not last_key:
        break
```

---

## Migration Checklist

### Pre-Migration

- [ ] Analyze PostgreSQL query logs (identify top 20 queries)
- [ ] Benchmark current p50/p99 latencies
- [ ] Prototype 5 most critical queries in DynamoDB
- [ ] Review design with backend team
- [ ] Set up DynamoDB tables in dev environment
- [ ] Create test data migration script
- [ ] Implement repository abstraction layer

### Phase 1: Dual-Write (Week 1-2)

- [ ] Deploy DynamoDB tables (dev, staging)
- [ ] Implement dual-write logic for all write operations
- [ ] Add feature flags for DynamoDB reads
- [ ] Enable DynamoDB reads for 10% of traffic
- [ ] Monitor data consistency (PostgreSQL vs DynamoDB)
- [ ] Set up CloudWatch dashboards

### Phase 2: Data Migration (Week 3-4)

- [ ] Export PostgreSQL data
- [ ] Transform data to DynamoDB format
- [ ] Perform bulk import to DynamoDB
- [ ] Verify data integrity (row counts, checksums)
- [ ] Test all read queries against DynamoDB
- [ ] Fix any data inconsistencies

### Phase 3: Read Migration (Week 5-7)

- [ ] Increase DynamoDB read traffic to 50%
- [ ] Monitor latency and error rates
- [ ] Optimize slow queries (add caching, adjust GSIs)
- [ ] Increase to 100% DynamoDB reads
- [ ] Keep PostgreSQL as fallback for 1 week

### Phase 4: Write Migration (Week 8-9)

- [ ] Switch all writes to DynamoDB only
- [ ] Stop dual-write logic
- [ ] Keep PostgreSQL as read-only backup
- [ ] Monitor for 30 days

### Phase 5: Decommission (Week 10-12)

- [ ] Export PostgreSQL for archival
- [ ] Shut down PostgreSQL database
- [ ] Remove dual-write code
- [ ] Clean up feature flags
- [ ] Document final DynamoDB setup

---

## Cost Optimization Checklist

- [ ] Enable Auto Scaling for Main table (target 70% utilization)
- [ ] Set TTL on UsageLog items (90-day expiration)
- [ ] Use eventually consistent reads for non-critical queries
- [ ] Implement ElastiCache (Redis) for hot data
- [ ] Monitor and optimize GSI projection types (consider KEYS_ONLY)
- [ ] Use BatchGetItem/BatchWriteItem for bulk operations
- [ ] Set up CloudWatch alarms for cost spikes
- [ ] Review and optimize item sizes (compress large fields)
- [ ] Consider moving large code/solutions to S3
- [ ] Implement sparse indexes (only populate when needed)

---

## Monitoring Checklist

### CloudWatch Metrics to Track

- [ ] ConsumedReadCapacityUnits (by table, by GSI)
- [ ] ConsumedWriteCapacityUnits (by table, by GSI)
- [ ] ProvisionedReadCapacityUnits (check for throttling)
- [ ] ProvisionedWriteCapacityUnits (check for throttling)
- [ ] UserErrors (4xx errors)
- [ ] SystemErrors (5xx errors)
- [ ] SuccessfulRequestLatency (p50, p99, p999)
- [ ] ThrottledRequests (should be 0)
- [ ] ConditionalCheckFailedRequests (for optimistic locking)

### Custom Application Metrics

- [ ] Query execution time (by query type)
- [ ] Cache hit rate (if using ElastiCache)
- [ ] Data consistency checks (dual-write phase)
- [ ] Failed transactions/rollbacks
- [ ] API endpoint latency (end-to-end)

### Cost Tracking

- [ ] Daily cost by table
- [ ] Cost by operation type (read, write, storage)
- [ ] GSI storage costs
- [ ] On-demand vs provisioned cost comparison
- [ ] Set budget alerts ($150/month threshold)

---

## Quick Django to DynamoDB Translation

| Django ORM | DynamoDB Equivalent |
|------------|-------------------|
| `Problem.objects.get(id=1)` | `table.get_item(Key={'PK': 'PROBLEM#...', 'SK': 'METADATA'})` |
| `Problem.objects.filter(platform='baekjoon')` | `table.query(IndexName='GSI1', KeyConditionExpression='GSI1PK = :pk', ...)` |
| `Problem.objects.filter(is_completed=True)` | `table.query(IndexName='GSI2', KeyConditionExpression='GSI2PK = :pk', ...)` |
| `problem.test_cases.all()` | `table.query(KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)', ...)` |
| `SearchHistory.objects.filter(user=user)` | `table.query(KeyConditionExpression='PK = :pk', ...)` |
| `SearchHistory.objects.filter(is_code_public=True)` | `table.query(IndexName='GSI1', KeyConditionExpression='GSI1PK = :pk', ...)` |
| `User.objects.get(email='...')` | `users_table.get_item(Key={'PK': 'USER#...', 'SK': 'METADATA'})` |
| `User.objects.get(google_id='...')` | `users_table.query(IndexName='GSI1', KeyConditionExpression='GSI1PK = :pk', ...)` |
| `UsageLog.objects.filter(user=user, created_at__gte=today)` | `table.query(KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)', ...)` |

---

## Performance Targets

| Operation | Target Latency | Current PostgreSQL | DynamoDB Expected |
|-----------|---------------|-------------------|------------------|
| Get problem by ID | <10ms | 15-30ms | 5-10ms |
| Get problem + test cases | <50ms | 50-100ms (N+1 risk) | 20-40ms (single query) |
| List problems (20 items) | <100ms | 80-150ms | 30-80ms |
| User history (20 items) | <50ms | 60-120ms | 20-50ms |
| Check daily usage | <10ms | 20-40ms | 5-10ms |
| Execute code (write) | <20ms | 30-60ms | 10-30ms |
| Public history feed | <100ms | 100-200ms | 40-100ms |

---

## Contact & Support

**For Questions:**
- Review full design: `/Users/gwonsoolee/algoitny/DYNAMODB_SCHEMA_DESIGN.md`
- Consult with django-backend-architect agent
- AWS DynamoDB documentation: https://docs.aws.amazon.com/dynamodb/

**Next Steps:**
1. Review this design with your backend team
2. Validate access patterns are complete
3. Run prototype queries in DynamoDB Local
4. Benchmark performance vs PostgreSQL
5. Begin Phase 1 implementation (dual-write)

---

**Last Updated:** 2025-01-15
**Version:** 1.0
