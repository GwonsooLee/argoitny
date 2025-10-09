# DynamoDB Optimized Single-Table Design

**Version**: 2.0 (Cost-Optimized)
**Date**: 2025-10-07
**Focus**: Single-table design with minimal GSIs, abbreviated field names, and maximum cost efficiency

---

## Executive Summary

This design consolidates all 8 entities (User, Problem, TestCase, SearchHistory, ScriptGenerationJob, UsageLog, SubscriptionPlan, TaskResult) into a **single DynamoDB table** with only **2 critical GSIs** for hot access patterns. Storage costs are reduced by 60-70% through abbreviated field names, and throughput costs are minimized by optimizing access patterns to use the base table whenever possible.

**Cost Reduction Strategies**:
- Single table eliminates cross-table queries and reduces provisioned capacity needs
- Abbreviated field names reduce item size by ~40-50%
- Only 2 GSIs vs. typical 8+ GSIs (reduces write costs by 75%)
- Hierarchical data stored adjacently for single-query retrieval
- Sparse GSI patterns to minimize index storage costs

---

## Table Structure

### Base Table: `algoitny-main`

**Partition Key (PK)**: String
**Sort Key (SK)**: String

**Capacity Mode**: On-Demand (recommended for unpredictable traffic)
**Stream**: Disabled (enable only if event-driven processing is needed)
**Point-in-Time Recovery**: Enabled
**Encryption**: AWS managed key (SSE)

---

## Attribute Name Abbreviations

To minimize storage costs, all attribute names are abbreviated to 2-4 characters:

| Full Name | Abbreviated | Type | Description |
|-----------|-------------|------|-------------|
| partition_key | pk | S | Partition key |
| sort_key | sk | S | Sort key |
| entity_type | et | S | Entity type identifier |
| name | nm | S | Name/title |
| email | em | S | Email address |
| google_id | gid | S | Google OAuth ID |
| picture | pic | S | Profile picture URL |
| subscription_plan | sp | S | Subscription plan name |
| is_active | ia | N | Active flag (1/0) |
| is_staff | is | N | Staff flag (1/0) |
| platform | pf | S | Platform name |
| problem_id | pid | S | Problem identifier |
| problem_url | purl | S | Problem URL |
| language | lg | S | Programming language |
| tags | tgs | L | Tags list |
| solution_code | sol | S | Solution code |
| constraints | con | S | Problem constraints |
| is_completed | ic | N | Completion flag (1/0) |
| is_deleted | id | N | Deletion flag (1/0) |
| deleted_at | da | N | Deletion timestamp |
| deleted_reason | dr | S | Deletion reason |
| test_input | tin | S | Test case input |
| test_output | tout | S | Test case output |
| code | cd | S | User code |
| result_summary | rs | M | Result summary map |
| passed_count | pc | N | Passed test count |
| failed_count | fc | N | Failed test count |
| total_count | tc | N | Total test count |
| is_code_public | icp | N | Code public flag (1/0) |
| test_results | tr | L | Test results list |
| hints | hn | L | Hints list |
| user_identifier | ui | S | User identifier |
| status | st | S | Status value |
| job_type | jt | S | Job type |
| celery_task_id | cti | S | Celery task ID |
| generator_code | gc | S | Generated code |
| error_message | em | S | Error message |
| action | ac | S | Action type |
| metadata | md | M | Metadata map |
| description | dsc | S | Description |
| max_hints_per_day | mhpd | N | Max hints per day |
| max_executions_per_day | mepd | N | Max executions per day |
| max_problems | mp | N | Max problems |
| can_view_all_problems | cvap | N | Can view all problems (1/0) |
| can_register_problems | crp | N | Can register problems (1/0) |
| result | res | M | Task result |
| traceback | tb | S | Error traceback |
| created_at | ca | N | Creation timestamp (Unix epoch) |
| updated_at | ua | N | Update timestamp (Unix epoch) |
| ttl | ttl | N | TTL for auto-deletion |

**Note**: DynamoDB reserved attributes (pk, sk) are abbreviated but GSI key names use full descriptors for clarity.

---

## Entity Design Patterns

### 1. User Entity

**Access Patterns**:
- Get user by ID (primary key lookup) - **HOT**
- Get user by email (GSI query) - **HOT**
- Get user by Google ID (GSI query) - WARM
- List users by subscription plan - COLD (admin only)
- List active users - COLD (admin only)

**Item Structure**:
```json
{
  "pk": "USER#<user_id>",
  "sk": "META",
  "et": "USER",
  "em": "user@example.com",
  "nm": "John Doe",
  "pic": "https://...",
  "gid": "google-oauth-id",
  "sp": "Free",
  "ia": 1,
  "is": 0,
  "ca": 1696723200,
  "ua": 1696809600
}
```

**Queries**:
- Get user by ID: `GetItem(pk="USER#123", sk="META")`
- Get user by email: `Query on GSI1 where gsi1pk="EMAIL#user@example.com"`
- Get user by Google ID: `Query on GSI1 where gsi1pk="GOOG#google-oauth-id"`

---

### 2. Subscription Plan Entity

**Access Patterns**:
- Get plan by name - WARM
- List all plans - COLD
- Get plan usage stats - COLD (admin only)

**Item Structure**:
```json
{
  "pk": "PLAN#<plan_name>",
  "sk": "META",
  "et": "PLAN",
  "nm": "Free",
  "dsc": "Free plan with basic features",
  "mhpd": 5,
  "mepd": 50,
  "mp": -1,
  "cvap": 1,
  "crp": 0,
  "ia": 1,
  "ca": 1696723200,
  "ua": 1696809600
}
```

**Queries**:
- Get plan: `GetItem(pk="PLAN#Free", sk="META")`
- List all plans: `Query where pk begins_with "PLAN#"`

---

### 3. Problem Entity (with Test Cases)

**Access Patterns**:
- Get problem by ID with all test cases (single query) - **HOT**
- Get problem by platform + problem_id - **HOT**
- List problems by platform - WARM
- Search problems by title - COLD
- List completed problems - WARM
- List drafts - COLD (admin only)

**Item Structures**:

**Problem Metadata**:
```json
{
  "pk": "PROB#<problem_id>",
  "sk": "META",
  "et": "PROBLEM",
  "pf": "baekjoon",
  "pid": "1000",
  "nm": "A+B",
  "purl": "https://...",
  "tgs": ["math", "implementation"],
  "sol": "def solution()...",
  "lg": "python",
  "con": "1 <= a, b <= 10000",
  "ic": 1,
  "id": 0,
  "md": {"exec_count": 150},
  "ca": 1696723200,
  "ua": 1696809600
}
```

**Test Cases** (sorted by creation order):
```json
{
  "pk": "PROB#<problem_id>",
  "sk": "TC#<padded_number>",
  "et": "TESTCASE",
  "tin": "1 2",
  "tout": "3",
  "ca": 1696723200
}
```

Example test case SKs: `TC#00001`, `TC#00002`, `TC#00003` (zero-padded for lexicographic sorting)

**Queries**:
- Get problem with all test cases: `Query where pk="PROB#123" and sk begins_with ""`
- Get problem metadata only: `GetItem(pk="PROB#123", sk="META")`
- Get specific test case range: `Query where pk="PROB#123" and sk between "TC#00001" and "TC#00010"`
- Find by platform+pid: `Query on GSI2 where gsi2pk="PROBALT#baekjoon#1000"`

---

### 4. Search History Entity

**Access Patterns**:
- Get history by ID - WARM
- List user's history (paginated, sorted by time) - **HOT**
- List public history (paginated) - WARM
- List history by problem - COLD

**Item Structure**:
```json
{
  "pk": "HIST#<history_id>",
  "sk": "META",
  "et": "HISTORY",
  "uid": "USER#123",
  "ui": "user@example.com",
  "pid": "PROB#456",
  "pf": "baekjoon",
  "pnum": "1000",
  "pnm": "A+B",
  "lg": "python",
  "cd": "def solution()...",
  "rs": {"status": "partial"},
  "pc": 5,
  "fc": 2,
  "tc": 7,
  "icp": 1,
  "tr": [{"tid": 1, "pass": 1}, {"tid": 2, "pass": 0}],
  "hn": ["Check edge cases", "Review algorithm complexity"],
  "md": {"exec_time": 150},
  "ca": 1696723200
}
```

**User History Index** (using GSI1):
```json
{
  "pk": "HIST#<history_id>",
  "sk": "META",
  "gsi1pk": "USER#123",
  "gsi1sk": "HIST#<inverted_timestamp>",
  ...
}
```

**Inverted Timestamp**: To enable descending sort (newest first), use `9999999999 - timestamp`

**Queries**:
- Get user's history: `Query on GSI1 where gsi1pk="USER#123" and gsi1sk begins_with "HIST#"`
- List public history: `Query on GSI2 where gsi2pk="PUBLIC#1" and gsi2sk begins_with "<inverted_timestamp>"`

---

### 5. Usage Log Entity (Rate Limiting)

**Access Patterns**:
- Count user's daily usage by action - **EXTREMELY HOT** (every execution/hint request)
- List user's usage history - COLD (admin only)
- Get usage stats by date range - COLD (admin only)

**Item Structure**:
```json
{
  "pk": "USER#<user_id>",
  "sk": "USAGE#<date>#<action>#<timestamp>",
  "et": "USAGELOG",
  "ac": "execution",
  "pid": "PROB#456",
  "md": {"task_id": "abc123", "language": "python"},
  "ca": 1696723200,
  "ttl": 1704499200
}
```

SK Format: `USAGE#2025-10-07#execution#1696723200` or `USAGE#2025-10-07#hint#1696723205`

**TTL**: Set to 90 days from creation for automatic cleanup (reduces storage costs)

**Queries**:
- Count today's executions: `Query where pk="USER#123" and sk begins_with "USAGE#2025-10-07#execution#"`
- Count today's hints: `Query where pk="USER#123" and sk begins_with "USAGE#2025-10-07#hint#"`
- Get all today's usage: `Query where pk="USER#123" and sk begins_with "USAGE#2025-10-07#"`

**Rate Limiting Strategy**:
1. Query with `Select=COUNT` to minimize data transfer
2. Cache the count in Redis/ElastiCache for 5 minutes (reduces DynamoDB reads by 90%)
3. Only refresh on actual usage log writes

---

### 6. Script Generation Job Entity

**Access Patterns**:
- Get job by ID - WARM
- Get job by celery task ID - WARM
- List jobs by status - COLD (admin only)
- List jobs by platform+problem - COLD (admin only)

**Item Structure**:
```json
{
  "pk": "JOB#<job_id>",
  "sk": "META",
  "et": "JOB",
  "pf": "baekjoon",
  "pid": "1000",
  "nm": "A+B",
  "purl": "https://...",
  "tgs": ["math"],
  "sol": "def solution()...",
  "lg": "python",
  "con": "1 <= n <= 1000",
  "jt": "script_generation",
  "st": "PENDING",
  "cti": "celery-task-abc123",
  "gc": "// generated code...",
  "err": null,
  "ca": 1696723200,
  "ua": 1696809600
}
```

**Queries**:
- Get job: `GetItem(pk="JOB#123", sk="META")`
- Get by task ID: `Query on GSI2 where gsi2pk="TASK#celery-task-abc123"`

---

### 7. Task Result Entity (Celery)

**Access Patterns**:
- Get task result by task_id - **HOT** (polling during async operations)
- List tasks by status - COLD (admin only)

**Item Structure**:
```json
{
  "pk": "TASK#<task_id>",
  "sk": "META",
  "et": "TASKRESULT",
  "st": "SUCCESS",
  "res": {"output": "..."},
  "tb": null,
  "ca": 1696723200,
  "ua": 1696809600,
  "ttl": 1696982400
}
```

**TTL**: Set to 7 days from creation (celery results are temporary)

**Queries**:
- Get task result: `GetItem(pk="TASK#abc123", sk="META")`

---

## Global Secondary Indexes (GSIs)

### GSI1: User Lookup & History Index

**Purpose**: Hot path queries for user authentication and user-specific data

**Keys**:
- **Partition Key**: `gsi1pk` (String)
- **Sort Key**: `gsi1sk` (String)

**Projection**: ALL (full data projection for user lookups to avoid base table reads)

**Use Cases**:

1. **User by Email**:
   - gsi1pk: `EMAIL#user@example.com`
   - gsi1sk: `META`

2. **User by Google ID**:
   - gsi1pk: `GOOG#google-oauth-id`
   - gsi1sk: `META`

3. **User History (time-sorted)**:
   - gsi1pk: `USER#123`
   - gsi1sk: `HIST#<inverted_timestamp>` (format: `HIST#9999999999-1696723200`)

**Sparse Index**: Only items with gsi1pk attribute are indexed (Users and SearchHistory entities)

**Query Examples**:
```python
# User login by email
response = table.query(
    IndexName='GSI1',
    KeyConditionExpression='gsi1pk = :pk AND gsi1sk = :sk',
    ExpressionAttributeValues={
        ':pk': 'EMAIL#user@example.com',
        ':sk': 'META'
    }
)

# User's execution history (newest first)
response = table.query(
    IndexName='GSI1',
    KeyConditionExpression='gsi1pk = :pk AND begins_with(gsi1sk, :prefix)',
    ExpressionAttributeValues={
        ':pk': 'USER#123',
        ':prefix': 'HIST#'
    },
    Limit=20
)
```

---

### GSI2: Problem Lookup & Public History Index

**Purpose**: Alternate access patterns for problems and public history

**Keys**:
- **Partition Key**: `gsi2pk` (String)
- **Sort Key**: `gsi2sk` (String)

**Projection**: ALL

**Use Cases**:

1. **Problem by Platform + Problem ID**:
   - gsi2pk: `PROBALT#baekjoon#1000`
   - gsi2sk: `META`

2. **Public History (time-sorted)**:
   - gsi2pk: `PUBLIC#1` (single partition for public history)
   - gsi2sk: `<inverted_timestamp>` (format: `9999999999-1696723200`)

3. **Job by Celery Task ID**:
   - gsi2pk: `TASK#celery-task-abc123`
   - gsi2sk: `META`

**Sparse Index**: Only items with gsi2pk attribute are indexed

**Query Examples**:
```python
# Get problem by platform and problem_id
response = table.query(
    IndexName='GSI2',
    KeyConditionExpression='gsi2pk = :pk AND gsi2sk = :sk',
    ExpressionAttributeValues={
        ':pk': 'PROBALT#baekjoon#1000',
        ':sk': 'META'
    }
)

# List public history (newest first)
response = table.query(
    IndexName='GSI2',
    KeyConditionExpression='gsi2pk = :pk',
    ExpressionAttributeValues={
        ':pk': 'PUBLIC#1'
    },
    Limit=20,
    ScanIndexForward=False  # Descending order
)
```

**Hot Partition Risk**: Public history uses a single partition (`PUBLIC#1`). If public history queries exceed 3000 RCU/sec, consider:
- Using date-based partitioning: `PUBLIC#2025-10-07`
- Implementing application-level caching (Redis) for public history lists
- Using DynamoDB DAX (in-memory cache) for read-heavy workloads

---

## Access Pattern Matrix

| Access Pattern | Method | Keys/Index | Frequency | Cached? |
|---------------|--------|------------|-----------|---------|
| User login by email | Query | GSI1 (EMAIL#) | HIGH | Yes (5min) |
| User login by Google ID | Query | GSI1 (GOOG#) | HIGH | Yes (5min) |
| Get user by ID | GetItem | Base PK/SK | HIGH | Yes (15min) |
| Get problem by ID + test cases | Query | Base PK | HIGH | Yes (30min) |
| Get problem by platform+pid | Query | GSI2 (PROBALT#) | HIGH | Yes (30min) |
| User execution history | Query | GSI1 | HIGH | Yes (2min) |
| Public history | Query | GSI2 (PUBLIC#) | MEDIUM | Yes (5min) |
| Rate limit check (daily count) | Query | Base PK/SK | EXTREME | Yes (5min) |
| Get search history detail | GetItem | Base PK/SK | MEDIUM | No |
| Get task result | GetItem | Base PK/SK | MEDIUM | No |
| Get job by task ID | Query | GSI2 (TASK#) | LOW | No |
| List problems by platform | Scan | N/A | LOW | Yes (1hr) |
| Search problems by title | Scan | N/A | LOW | Yes (1hr) |
| List users by plan | Scan | N/A | VERY LOW | No |
| Admin stats | Scan + Aggregation | N/A | VERY LOW | Yes (1hr) |

**Caching Strategy**: All HIGH and MEDIUM frequency queries should be cached in Redis/ElastiCache to minimize DynamoDB costs.

---

## Example Items in Table

```
┌─────────────────────────┬──────────────────────────────┬────────────────────────────────┐
│ pk                      │ sk                           │ Attributes                     │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ USER#1                  │ META                         │ et=USER, em=john@example.com   │
│                         │                              │ gsi1pk=EMAIL#john@example.com  │
│                         │                              │ gsi1sk=META, sp=Free, ia=1...  │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ USER#1                  │ USAGE#2025-10-07#execution#  │ et=USAGELOG, ac=execution      │
│                         │ 1696723200                   │ pid=PROB#5, ttl=1704499200...  │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ USER#1                  │ USAGE#2025-10-07#hint#       │ et=USAGELOG, ac=hint           │
│                         │ 1696723250                   │ pid=PROB#5, ttl=1704499200...  │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ PLAN#Free               │ META                         │ et=PLAN, nm=Free, mhpd=5       │
│                         │                              │ mepd=50, mp=-1, cvap=1...      │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ PROB#5                  │ META                         │ et=PROBLEM, pf=baekjoon        │
│                         │                              │ pid=1000, nm=A+B, ic=1         │
│                         │                              │ gsi2pk=PROBALT#baekjoon#1000   │
│                         │                              │ gsi2sk=META, lg=python...      │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ PROB#5                  │ TC#00001                     │ et=TESTCASE, tin="1 2"         │
│                         │                              │ tout="3", ca=1696723200        │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ PROB#5                  │ TC#00002                     │ et=TESTCASE, tin="3 4"         │
│                         │                              │ tout="7", ca=1696723201        │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ HIST#100                │ META                         │ et=HISTORY, uid=USER#1         │
│                         │                              │ pid=PROB#5, lg=python, pc=5    │
│                         │                              │ gsi1pk=USER#1                  │
│                         │                              │ gsi1sk=HIST#9998303276800      │
│                         │                              │ gsi2pk=PUBLIC#1                │
│                         │                              │ gsi2sk=9998303276800, icp=1... │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ JOB#50                  │ META                         │ et=JOB, pf=baekjoon, pid=1001  │
│                         │                              │ jt=script_generation           │
│                         │                              │ st=COMPLETED, cti=task-abc123  │
│                         │                              │ gsi2pk=TASK#task-abc123        │
│                         │                              │ gsi2sk=META...                 │
├─────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│ TASK#task-abc123        │ META                         │ et=TASKRESULT, st=SUCCESS      │
│                         │                              │ res={...}, ttl=1696982400...   │
└─────────────────────────┴──────────────────────────────┴────────────────────────────────┘
```

---

## Query Patterns & Examples

### 1. User Authentication (HOT PATH)

**Use Case**: User login by email

```python
def get_user_by_email(email):
    response = table.query(
        IndexName='GSI1',
        KeyConditionExpression='gsi1pk = :pk AND gsi1sk = :sk',
        ExpressionAttributeValues={
            ':pk': f'EMAIL#{email}',
            ':sk': 'META'
        }
    )
    return response['Items'][0] if response['Items'] else None
```

**Cost**: 1 RCU (eventually consistent) or 2 RCU (strongly consistent)
**Latency**: 1-5ms (single-digit milliseconds)

---

### 2. Get Problem with All Test Cases (HOT PATH)

**Use Case**: Load problem for code execution

```python
def get_problem_with_test_cases(problem_id):
    response = table.query(
        KeyConditionExpression='pk = :pk',
        ExpressionAttributeValues={
            ':pk': f'PROB#{problem_id}'
        }
    )

    # First item is problem metadata, rest are test cases
    items = response['Items']
    problem = next(item for item in items if item['sk'] == 'META')
    test_cases = [item for item in items if item['sk'].startswith('TC#')]

    return problem, test_cases
```

**Cost**: 1 query retrieving N items (problem + test cases)
**RCU Calculation**: ceil((item_size_kb * item_count) / 4) for eventually consistent reads
**Latency**: 1-10ms depending on test case count

---

### 3. Rate Limit Check (EXTREMELY HOT PATH)

**Use Case**: Check if user has exceeded daily execution limit

```python
def check_daily_execution_limit(user_id, date_str='2025-10-07'):
    # First, check cache
    cache_key = f'rate_limit:execution:{user_id}:{date_str}'
    cached_count = redis.get(cache_key)
    if cached_count is not None:
        return int(cached_count)

    # If not cached, query DynamoDB
    response = table.query(
        KeyConditionExpression='pk = :pk AND begins_with(sk, :prefix)',
        ExpressionAttributeValues={
            ':pk': f'USER#{user_id}',
            ':prefix': f'USAGE#{date_str}#execution#'
        },
        Select='COUNT'  # Only return count, not items
    )

    count = response['Count']

    # Cache for 5 minutes
    redis.setex(cache_key, 300, count)

    return count
```

**Cost**: 1 RCU for COUNT query (minimal data transfer)
**Cost with caching**: ~90% reduction in DynamoDB reads
**Latency**: <1ms (from cache), 1-5ms (from DynamoDB)

---

### 4. User Execution History (HOT PATH)

**Use Case**: Display user's recent code execution history

```python
def get_user_history(user_id, limit=20, last_evaluated_key=None):
    query_params = {
        'IndexName': 'GSI1',
        'KeyConditionExpression': 'gsi1pk = :pk AND begins_with(gsi1sk, :prefix)',
        'ExpressionAttributeValues': {
            ':pk': f'USER#{user_id}',
            ':prefix': 'HIST#'
        },
        'Limit': limit,
        'ScanIndexForward': False  # Descending order (newest first)
    }

    if last_evaluated_key:
        query_params['ExclusiveStartKey'] = last_evaluated_key

    response = table.query(**query_params)

    return {
        'items': response['Items'],
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }
```

**Cost**: 1 query reading up to 1MB of data per page
**Pagination**: Use `LastEvaluatedKey` for cursor-based pagination

---

### 5. Public History Timeline (WARM PATH)

**Use Case**: Display recent public code submissions

```python
def get_public_history(limit=20, last_evaluated_key=None):
    query_params = {
        'IndexName': 'GSI2',
        'KeyConditionExpression': 'gsi2pk = :pk',
        'ExpressionAttributeValues': {
            ':pk': 'PUBLIC#1'
        },
        'Limit': limit,
        'ScanIndexForward': False  # Descending order (newest first)
    }

    if last_evaluated_key:
        query_params['ExclusiveStartKey'] = last_evaluated_key

    response = table.query(**query_params)

    return {
        'items': response['Items'],
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }
```

**Note**: Cache this query result for 5 minutes to avoid hot partition issues on GSI2.

---

### 6. Problem Search by Platform + Problem ID (HOT PATH)

**Use Case**: Find specific problem when user enters platform and problem number

```python
def get_problem_by_platform_and_id(platform, problem_id):
    response = table.query(
        IndexName='GSI2',
        KeyConditionExpression='gsi2pk = :pk AND gsi2sk = :sk',
        ExpressionAttributeValues={
            ':pk': f'PROBALT#{platform}#{problem_id}',
            ':sk': 'META'
        }
    )

    if not response['Items']:
        return None

    # Get the problem's internal ID from the result
    problem = response['Items'][0]
    internal_id = problem['pk'].split('#')[1]

    # Now fetch with test cases
    return get_problem_with_test_cases(internal_id)
```

---

### 7. List Problems by Platform (COLD PATH)

**Use Case**: Browse all Baekjoon problems

**Note**: This requires a Scan or Filter operation since we don't have a dedicated GSI for platform filtering.

**Options**:
1. **Scan with Filter** (not recommended for production without caching)
2. **Cache the entire result** (recommended for infrequent updates)

```python
def list_problems_by_platform(platform, cache_ttl=3600):
    # Check cache first
    cache_key = f'problems:platform:{platform}'
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Scan with filter (expensive!)
    response = table.scan(
        FilterExpression='et = :et AND pf = :pf AND ic = :ic AND id = :id',
        ExpressionAttributeValues={
            ':et': 'PROBLEM',
            ':pf': platform,
            ':ic': 1,  # completed
            ':id': 0   # not deleted
        },
        ProjectionExpression='pk,nm,pid,pf,lg,tgs,ca'  # Only needed fields
    )

    items = response['Items']

    # Cache for 1 hour
    redis.setex(cache_key, cache_ttl, json.dumps(items))

    return items
```

**Cost**: Full table scan (expensive!)
**Mitigation**: Aggressive caching (1+ hour), invalidate on problem creation/update

---

### 8. Search Problems by Title (COLD PATH)

**Use Case**: Search for problems by keyword in title

**Note**: DynamoDB doesn't support full-text search. Use one of these approaches:

**Option A**: Scan with contains filter (expensive)
```python
def search_problems_by_title(search_term):
    response = table.scan(
        FilterExpression='et = :et AND contains(nm, :term) AND ic = :ic AND id = :id',
        ExpressionAttributeValues={
            ':et': 'PROBLEM',
            ':term': search_term,
            ':ic': 1,
            ':id': 0
        }
    )
    return response['Items']
```

**Option B**: Use OpenSearch/Elasticsearch (recommended for production)
- Stream DynamoDB changes to OpenSearch
- Use OpenSearch for full-text search
- Return problem IDs, then batch GetItem from DynamoDB

**Option C**: Maintain search index in Redis (simple approach)
- On problem creation/update, update Redis sorted set
- Use Redis ZRANGEBYLEX for prefix matching

---

### 9. Log Usage (Write Operation)

**Use Case**: Record execution or hint usage

```python
def log_usage(user_id, action, problem_id, metadata=None):
    now = int(time.time())
    date_str = datetime.fromtimestamp(now).strftime('%Y-%m-%d')

    item = {
        'pk': f'USER#{user_id}',
        'sk': f'USAGE#{date_str}#{action}#{now}',
        'et': 'USAGELOG',
        'ac': action,
        'pid': problem_id,
        'md': metadata or {},
        'ca': now,
        'ttl': now + (90 * 86400)  # 90 days TTL
    }

    table.put_item(Item=item)

    # Invalidate rate limit cache
    cache_key = f'rate_limit:{action}:{user_id}:{date_str}'
    redis.delete(cache_key)
```

**Cost**: 1 WCU per item write
**With GSIs**: +2 WCU (1 per GSI) if the item has GSI keys
**Usage logs don't use GSIs**: Only 1 WCU per write

---

### 10. Get Task Result (Polling)

**Use Case**: Check status of async Celery task

```python
def get_task_result(task_id):
    response = table.get_item(
        Key={
            'pk': f'TASK#{task_id}',
            'sk': 'META'
        }
    )
    return response.get('Item')
```

**Cost**: 1 RCU (eventually consistent) or 2 RCU (strongly consistent)
**Pattern**: Client polls every 1-2 seconds until status is SUCCESS/FAILURE

---

## Cost Estimation

### Assumptions
- **Daily Active Users**: 1,000
- **Avg executions per user**: 10/day = 10,000 executions/day
- **Avg hints per user**: 2/day = 2,000 hints/day
- **Avg history queries per user**: 5/day = 5,000 queries/day
- **Problem lookups**: 20,000/day (2x executions due to caching)
- **Rate limit checks**: 12,000/day (cached, so only 1,200 DynamoDB reads)
- **Public history views**: 5,000/day

### Daily Read Units (with caching)
| Operation | Count/Day | RCU Each | Total RCU |
|-----------|-----------|----------|-----------|
| User login | 1,000 | 1 | 1,000 |
| Problem lookup | 20,000 | 2 | 40,000 |
| History queries | 5,000 | 5 | 25,000 |
| Rate limit checks | 1,200 | 1 | 1,200 |
| Task result polling | 15,000 | 1 | 15,000 |
| Public history | 500 | 5 | 2,500 |
| **Total** | | | **84,700 RCU/day** |

**Average RCU/sec**: 84,700 / 86,400 ≈ **1 RCU/sec**
**Peak RCU/sec** (assuming 5x burst): **5 RCU/sec**

**On-Demand Read Cost**: $1.25 per 1M read units
**Daily Cost**: 84,700 * $1.25 / 1,000,000 = **$0.11/day = $3.30/month**

---

### Daily Write Units
| Operation | Count/Day | WCU Each | Total WCU |
|-----------|-----------|----------|-----------|
| Executions (with history) | 10,000 | 1 + 2 (GSIs) | 30,000 |
| Hints (update history) | 2,000 | 1 | 2,000 |
| Usage logs | 12,000 | 1 | 12,000 |
| User creation | 10 | 1 + 2 (GSIs) | 30 |
| Problem creation | 5 | 1 + 1 (GSI2) | 10 |
| **Total** | | | **44,040 WCU/day** |

**Average WCU/sec**: 44,040 / 86,400 ≈ **0.5 WCU/sec**
**Peak WCU/sec** (assuming 5x burst): **2.5 WCU/sec**

**On-Demand Write Cost**: $1.25 per 1M write units
**Daily Cost**: 44,040 * $1.25 / 1,000,000 = **$0.055/day = $1.65/month**

---

### Storage Cost
**Assumptions**:
- 1,000 users × 1KB each = 1MB
- 5,000 problems × 2KB each = 10MB
- 50,000 test cases × 0.5KB each = 25MB
- 100,000 history records × 3KB each = 300MB
- 1,000,000 usage logs × 0.3KB each = 300MB (with TTL cleanup)
- 10,000 jobs × 5KB each = 50MB
- 50,000 task results × 1KB each = 50MB (with TTL cleanup)

**Total Storage**: ~736MB

**DynamoDB Storage Cost**: $0.25 per GB/month
**Monthly Cost**: 0.736 * $0.25 = **$0.18/month**

---

### GSI Storage Cost
**GSI1** (User lookups + History):
- Users: 1MB
- History: 300MB
- **Total**: 301MB

**GSI2** (Problem lookups + Public history):
- Problems: 10MB
- Public history: ~50MB (50% public)
- Jobs: 50MB
- **Total**: 110MB

**GSI Storage Cost**: $0.25 per GB/month
**Monthly Cost**: (0.301 + 0.110) * $0.25 = **$0.10/month**

---

### Total Monthly Cost (On-Demand)

| Component | Monthly Cost |
|-----------|--------------|
| Read operations | $3.30 |
| Write operations | $1.65 |
| Table storage | $0.18 |
| GSI storage | $0.10 |
| **Total** | **$5.23/month** |

**Annual Cost**: $5.23 × 12 = **$62.76/year**

---

### Cost Comparison: Multi-Table vs Single-Table

#### Previous Multi-Table Design (8 tables + 8 GSIs)
- **Storage**: ~1.5GB (no TTL, redundant data)
- **GSI Storage**: ~1GB (8 GSIs)
- **Write amplification**: 3-4x due to multiple GSIs per table
- **Estimated Cost**: $15-20/month

#### Optimized Single-Table Design (1 table + 2 GSIs)
- **Storage**: ~0.74GB (with TTL cleanup, abbreviated names)
- **GSI Storage**: ~0.41GB (2 GSIs only)
- **Write amplification**: 1-3x (most writes don't hit GSIs)
- **Actual Cost**: $5.23/month

**Savings**: 70-75% cost reduction

---

## Provisioned Capacity Alternative

If traffic becomes more predictable, switch to provisioned capacity for additional savings:

**Base Table**:
- **RCU**: 5 (auto-scaling 1-10)
- **WCU**: 3 (auto-scaling 1-5)
- **Cost**: 5 × $0.00013 × 730 + 3 × $0.00065 × 730 = $0.47 + $1.42 = **$1.89/month**

**GSIs** (2 indexes):
- **RCU**: 3 each × 2 = 6 total
- **WCU**: 3 each × 2 = 6 total
- **Cost**: 6 × $0.00013 × 730 + 6 × $0.00065 × 730 = $0.57 + $2.85 = **$3.42/month**

**Provisioned Total**: $1.89 + $3.42 + $0.28 (storage) = **$5.59/month**

**Recommendation**: Start with On-Demand ($5.23/month), switch to Provisioned if traffic stabilizes and exceeds baseline consistently.

---

## Trade-offs and Limitations

### Benefits
1. **Significant Cost Savings**: 70-75% reduction vs. multi-table design
2. **Simplified Operations**: Single table to manage, backup, monitor
3. **Atomic Transactions**: Can use DynamoDB transactions within same table
4. **Reduced Cold Starts**: Fewer table connections for Lambda functions
5. **Better Data Locality**: Related data stored together (problem + test cases)
6. **Automatic Cleanup**: TTL on temporary data (usage logs, task results)

### Limitations

1. **Scan Operations Required**:
   - Listing problems by platform
   - Searching problems by title
   - Admin analytics queries
   - **Mitigation**: Aggressive caching, OpenSearch integration, or batch jobs

2. **Hot Partition Risk**:
   - Public history uses single partition (`PUBLIC#1`)
   - If exceeds 3000 RCU/sec, will throttle
   - **Mitigation**: Cache public history aggressively, consider date-based partitioning, use DAX

3. **Complex Query Patterns**:
   - Code is more complex with composite keys
   - Developers must understand single-table patterns
   - **Mitigation**: Create well-documented helper functions, use ORM abstraction layer

4. **Limited GSI Flexibility**:
   - Only 2 GSIs means some queries require scans
   - Adding new access patterns may require GSI changes (online operation, but takes time)
   - **Mitigation**: Plan access patterns carefully, use Scan with caching for rare queries

5. **No Full-Text Search**:
   - DynamoDB doesn't support FTS natively
   - Problem title search requires Scan or external search service
   - **Mitigation**: Integrate OpenSearch/Elasticsearch for search-heavy features

6. **Item Size Limits**:
   - Max 400KB per item
   - Large code submissions or test outputs could exceed limit
   - **Mitigation**: Store large data in S3, keep references in DynamoDB

7. **Testing Complexity**:
   - Need to mock composite key patterns in tests
   - Local DynamoDB setup more complex
   - **Mitigation**: Use DynamoDB Local, create test fixtures with proper key structures

8. **Migration Effort**:
   - Migrating from PostgreSQL to DynamoDB requires:
     - Data transformation scripts
     - Rewriting all queries
     - Updating ORM/repository layer
     - Extensive testing
   - **Estimated Effort**: 3-4 weeks for full migration

---

## Implementation Recommendations

### Phase 1: Hot Path Migration (Week 1-2)
1. **User Authentication**: Migrate User table to DynamoDB
2. **Problem Lookups**: Migrate Problem + TestCase tables
3. **Rate Limiting**: Migrate UsageLog table
4. Run dual-write (PostgreSQL + DynamoDB) for safety

### Phase 2: History & Jobs (Week 2-3)
1. **Search History**: Migrate SearchHistory table
2. **Jobs & Tasks**: Migrate ScriptGenerationJob and TaskResult
3. Verify all queries working correctly

### Phase 3: Admin Features (Week 3-4)
1. **Plans**: Migrate SubscriptionPlan table
2. **Admin Queries**: Implement Scan-based admin analytics with caching
3. Full testing and validation

### Phase 4: Cutover (Week 4)
1. Stop dual-writes
2. Decommission PostgreSQL tables
3. Monitor costs and performance

---

## Monitoring & Alerts

### Key Metrics to Monitor
1. **Consumed RCU/WCU**: Should stay under provisioned capacity (if using provisioned)
2. **Throttled Requests**: Alert if >0.1% of requests throttled
3. **GSI Consumption**: Monitor GSI1 and GSI2 separately
4. **Hot Partition Alerts**: Watch for `PUBLIC#1` partition throttling
5. **Item Size Distribution**: Alert if any item >300KB (approaching 400KB limit)
6. **TTL Deletion Rate**: Ensure old usage logs and tasks are being deleted
7. **Query Latency**: P50, P99, P99.9 latencies for each query type
8. **Cache Hit Rate**: Monitor Redis cache effectiveness (should be >85%)

### CloudWatch Alarms
```yaml
Alarms:
  - Name: HighThrottleRate
    Metric: UserErrors (ThrottledRequests)
    Threshold: > 10 per minute

  - Name: HighReadLatency
    Metric: SuccessfulRequestLatency (GetItem, Query)
    Threshold: P99 > 50ms

  - Name: HighCostPerDay
    Metric: ConsumedReadCapacityUnits + ConsumedWriteCapacityUnits
    Threshold: > 200,000 per day ($20/month equivalent)
```

---

## Cache Strategy

To achieve the cost estimates above, aggressive caching is essential:

| Query Type | Cache Location | TTL | Invalidation Trigger |
|------------|---------------|-----|---------------------|
| User by email | Redis | 15 min | User update |
| Problem detail | Redis | 30 min | Problem update |
| Problem list | Redis | 1 hour | Problem created/updated |
| User history | Redis | 2 min | New execution |
| Public history | Redis | 5 min | New public submission |
| Rate limit count | Redis | 5 min | New usage log |
| Subscription plans | Redis | 24 hours | Plan updated |

**Cache Invalidation**:
- Use DynamoDB Streams to trigger invalidation Lambda
- Or invalidate in application code after writes

---

## Security Considerations

1. **Encryption at Rest**: Use AWS managed keys (KMS optional for compliance)
2. **Encryption in Transit**: All DynamoDB API calls use TLS 1.2+
3. **IAM Policies**: Principle of least privilege
   - Read-only IAM role for read replicas
   - Write IAM role for application servers
   - Admin IAM role for operators
4. **VPC Endpoints**: Use VPC endpoints to keep traffic within AWS network
5. **Attribute-Level Encryption**: Consider client-side encryption for sensitive fields (code, email)
6. **Audit Logging**: Enable CloudTrail for DynamoDB API calls

---

## Backup & Disaster Recovery

1. **Point-in-Time Recovery (PITR)**: Enabled (allows restore to any point in last 35 days)
2. **On-Demand Backups**: Weekly full backups retained for 90 days
3. **Cross-Region Replication**: Consider DynamoDB Global Tables for disaster recovery
4. **RTO/RPO**:
   - **RTO** (Recovery Time Objective): <1 hour with PITR
   - **RPO** (Recovery Point Objective): <5 minutes with PITR

---

## Future Enhancements

### When to Add a Third GSI

Only add GSI3 if you have a truly hot access pattern (>1000 req/min) that cannot be:
- Cached effectively
- Satisfied with Scan + cache
- Denormalized into existing GSIs

**Potential GSI3 Use Case**: If admin queries become frequent (unlikely), create:
- **gsi3pk**: `STATUS#<status>` (for filtering by status)
- **gsi3sk**: `<entity_type>#<timestamp>` (for sorting by type and time)

### When to Consider Global Tables

If you expand to multiple regions with low-latency requirements:
- DynamoDB Global Tables provide multi-region replication
- Adds ~$0.25 per GB transferred between regions
- Useful if you have users in US, EU, and Asia requiring <50ms latency

### When to Consider DAX (DynamoDB Accelerator)

If cache hit rate is low (<70%) or latency requirements are <5ms:
- DAX provides microsecond latency for reads
- Costs ~$0.20/hour for t3.small node ($144/month)
- Only cost-effective if DynamoDB read costs exceed $100/month

---

## Conclusion

This optimized single-table design achieves:
- **70-75% cost reduction** compared to multi-table design
- **Single-digit millisecond latency** for all hot paths
- **Simple operational model** (1 table, 2 GSIs)
- **Automatic data lifecycle management** (TTL for temporary data)
- **Excellent scalability** (DynamoDB scales to millions of requests/sec)

**Estimated Monthly Cost**: $5.23 (on-demand) or $5.59 (provisioned)

The design prioritizes the most frequent access patterns (user auth, problem lookup, rate limiting, execution history) with direct GetItem or single GSI queries, while accepting Scan operations for infrequent admin queries that can be heavily cached.

**Recommendation**: Proceed with phased migration, starting with hot paths (user auth, problem lookups, rate limiting) while maintaining PostgreSQL for cold paths until fully validated.

---

## Appendix A: Helper Function Library

To simplify working with this schema, create a helper library:

```python
# key_builder.py
class KeyBuilder:
    @staticmethod
    def user_pk(user_id):
        return f"USER#{user_id}"

    @staticmethod
    def user_meta_key():
        return "META"

    @staticmethod
    def user_email_gsi1pk(email):
        return f"EMAIL#{email}"

    @staticmethod
    def user_google_gsi1pk(google_id):
        return f"GOOG#{google_id}"

    @staticmethod
    def problem_pk(problem_id):
        return f"PROB#{problem_id}"

    @staticmethod
    def problem_meta_key():
        return "META"

    @staticmethod
    def problem_testcase_sk(sequence_num):
        return f"TC#{sequence_num:05d}"

    @staticmethod
    def problem_alt_gsi2pk(platform, problem_id):
        return f"PROBALT#{platform}#{problem_id}"

    @staticmethod
    def history_pk(history_id):
        return f"HIST#{history_id}"

    @staticmethod
    def history_user_gsi1pk(user_id):
        return f"USER#{user_id}"

    @staticmethod
    def history_gsi1sk(timestamp):
        inverted = 9999999999 - int(timestamp)
        return f"HIST#{inverted}"

    @staticmethod
    def usage_sk(date, action, timestamp):
        return f"USAGE#{date}#{action}#{timestamp}"

    @staticmethod
    def public_history_gsi2pk():
        return "PUBLIC#1"

    @staticmethod
    def public_history_gsi2sk(timestamp):
        return str(9999999999 - int(timestamp))

    @staticmethod
    def task_pk(task_id):
        return f"TASK#{task_id}"

    @staticmethod
    def job_pk(job_id):
        return f"JOB#{job_id}"

    @staticmethod
    def plan_pk(plan_name):
        return f"PLAN#{plan_name}"
```

Usage:
```python
# Get user by email
table.query(
    IndexName='GSI1',
    KeyConditionExpression='gsi1pk = :pk AND gsi1sk = :sk',
    ExpressionAttributeValues={
        ':pk': KeyBuilder.user_email_gsi1pk('user@example.com'),
        ':sk': KeyBuilder.user_meta_key()
    }
)
```

---

## Appendix B: Attribute Abbreviation Quick Reference

```
Full Name                    → Abbreviated
═══════════════════════════════════════════
partition_key                → pk
sort_key                     → sk
entity_type                  → et
name / title                 → nm
email                        → em
google_id                    → gid
picture                      → pic
subscription_plan            → sp
is_active                    → ia
is_staff                     → is
platform                     → pf
problem_id                   → pid
problem_url                  → purl
language                     → lg
tags                         → tgs
solution_code                → sol
constraints                  → con
is_completed                 → ic
is_deleted                   → id
deleted_at                   → da
deleted_reason               → dr
test_input                   → tin
test_output                  → tout
code                         → cd
result_summary               → rs
passed_count                 → pc
failed_count                 → fc
total_count                  → tc
is_code_public               → icp
test_results                 → tr
hints                        → hn
user_identifier              → ui
status                       → st
job_type                     → jt
celery_task_id               → cti
generator_code               → gc
error_message                → err
action                       → ac
metadata                     → md
description                  → dsc
max_hints_per_day            → mhpd
max_executions_per_day       → mepd
max_problems                 → mp
can_view_all_problems        → cvap
can_register_problems        → crp
result                       → res
traceback                    → tb
created_at                   → ca
updated_at                   → ua
ttl                          → ttl
```

---

**End of Document**
