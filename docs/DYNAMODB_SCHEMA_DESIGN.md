# DynamoDB Schema Design for AlgoItny

## Executive Summary

This document presents a comprehensive DynamoDB table design to replace the current PostgreSQL/MySQL relational database for the AlgoItny algorithmic problem-solving platform. The design uses a **hybrid approach**: combining single-table design for hot-path queries with separate tables for infrequently accessed administrative data.

**Key Design Decisions:**
- **Single Table Design** for core entities (Problems, TestCases, SearchHistory, UsageLog)
- **Separate Tables** for user management and subscription plans (low-frequency admin operations)
- **Optimized for read-heavy workloads** with strategic GSI placement
- **Cost-optimized** through minimal index usage and efficient key design

---

## Current Django Models Analysis

### Entities Identified

1. **User** - Custom user with Google OAuth authentication
2. **SubscriptionPlan** - Configurable plans with usage limits
3. **Problem** - Algorithm problems from various platforms
4. **TestCase** - Input/output test cases for problems
5. **SearchHistory** - Execution history with results and hints
6. **ScriptGenerationJob** - Async job tracking for test generation
7. **UsageLog** - Daily usage tracking for rate limiting

### Current Relationships

```
User 1:N SearchHistory
User 1:N UsageLog
User N:1 SubscriptionPlan
Problem 1:N TestCase
Problem 1:N SearchHistory
Problem 1:N UsageLog
```

---

## Access Pattern Analysis

### High-Frequency Access Patterns (Hot Path)

#### Problem Access
1. **Get problem by ID** - Single item fetch
2. **Get problem by platform + problem_id** - Unique constraint lookup
3. **List problems with filters** - Search by platform, title, language
4. **List completed problems** - Filter by is_completed=true
5. **List draft problems** - Filter by is_completed=false (admin only)
6. **Get problem with test cases** - 1:N relationship fetch

#### Search History Access
7. **Get user's search history** - User-specific timeline
8. **List public search history** - Global timeline of public submissions
9. **Mixed visibility query** - Own history + public history from others
10. **Get search history detail** - Single item with test results
11. **Filter history by platform/language** - Search within history

#### Code Execution
12. **Execute code** - Create new SearchHistory record
13. **Get test cases for problem** - Fetch all test cases for execution

#### Usage Tracking & Rate Limiting
14. **Check daily usage** - Count today's hints/executions per user
15. **Log usage action** - Create UsageLog entry
16. **Get user plan limits** - Fetch user's subscription plan

#### Hint Generation
17. **Generate hints** - Update SearchHistory with AI hints
18. **Get hints** - Fetch hints from SearchHistory

### Medium-Frequency Access Patterns

#### Script Generation Jobs
19. **Create generation job** - Create ScriptGenerationJob
20. **Get job by ID** - Fetch job status
21. **List jobs by type** - Filter by job_type
22. **Update job status** - Update status + results

### Low-Frequency Access Patterns (Admin)

#### User Management
23. **List all users** - Admin dashboard
24. **Get user by email** - Login/lookup
25. **Get user by google_id** - OAuth lookup
26. **Update user plan** - Admin action
27. **Filter users by plan** - Admin reporting

#### Subscription Management
28. **List all plans** - Admin + user selection
29. **Get plan by name** - Plan lookup
30. **Create/update plan** - Admin action

#### Analytics
31. **Get user stats** - Execution counts by platform/language
32. **Get usage stats** - Admin dashboard aggregations
33. **Top users by activity** - Leaderboard

---

## DynamoDB Table Design

### Design Philosophy

Given the access patterns, I'm recommending a **hybrid approach**:

1. **Main Table (AlgoItny-Main)**: Single-table design for hot-path queries
   - Problems, TestCases, SearchHistory, UsageLog, ScriptGenerationJobs
   - Optimizes for the 95% of queries that are user-facing

2. **Users Table (AlgoItny-Users)**: Separate table for user data
   - Isolates user authentication/management
   - Admin operations don't impact main table performance
   - Simplifies security and access control

3. **Plans Table (AlgoItny-Plans)**: Separate table for subscription plans
   - Very low write frequency (admin only)
   - Can use on-demand pricing
   - Simple key-value structure

---

## Table 1: AlgoItny-Main (Single Table Design)

### Primary Key Structure

**Partition Key (PK)**: Composite string that identifies entity type and ID
**Sort Key (SK)**: Composite string for hierarchical data and sorting

### Entity Design Patterns

#### 1. Problem Entity

**Primary Record:**
```
PK: PROBLEM#{platform}#{problem_id}
SK: METADATA
```

**Attributes:**
```json
{
  "PK": "PROBLEM#baekjoon#1000",
  "SK": "METADATA",
  "EntityType": "Problem",
  "InternalId": "uuid-or-numeric-id",
  "Platform": "baekjoon",
  "ProblemId": "1000",
  "Title": "A+B",
  "ProblemUrl": "https://www.acmicpc.net/problem/1000",
  "Tags": ["math", "implementation"],
  "SolutionCode": "a, b = map(int, input().split())\nprint(a + b)",
  "Language": "python",
  "Constraints": "1 <= a, b <= 10",
  "IsCompleted": true,
  "IsDeleted": false,
  "DeletedAt": null,
  "DeletedReason": null,
  "Metadata": {
    "execution_count": 150,
    "difficulty": "easy"
  },
  "CreatedAt": "2025-01-15T10:30:00Z",
  "UpdatedAt": "2025-01-15T10:30:00Z",
  "GSI1PK": "PLATFORM#baekjoon",
  "GSI1SK": "2025-01-15T10:30:00Z",
  "GSI2PK": "COMPLETED#true",
  "GSI2SK": "2025-01-15T10:30:00Z",
  "GSI3PK": "LANGUAGE#python",
  "GSI3SK": "2025-01-15T10:30:00Z"
}
```

**Why this design:**
- PK combines platform + problem_id for natural unique lookups
- SK=METADATA distinguishes problem record from its test cases
- GSI overloading enables multiple access patterns
- InternalId maintains compatibility with existing numeric IDs

#### 2. TestCase Entity (Child of Problem)

```
PK: PROBLEM#{platform}#{problem_id}
SK: TESTCASE#{timestamp}#{uuid}
```

**Attributes:**
```json
{
  "PK": "PROBLEM#baekjoon#1000",
  "SK": "TESTCASE#2025-01-15T10:30:00Z#abc123",
  "EntityType": "TestCase",
  "TestCaseId": "abc123",
  "Input": "1 2",
  "Output": "3",
  "CreatedAt": "2025-01-15T10:30:00Z"
}
```

**Why this design:**
- Same PK as parent problem enables single-query fetch of problem + all test cases
- SK starts with TESTCASE# for easy filtering
- Timestamp in SK provides natural ordering
- Query pattern: `Query(PK="PROBLEM#baekjoon#1000", SK begins_with "TESTCASE#")`

#### 3. SearchHistory Entity

**Primary Record:**
```
PK: USER#{user_id}
SK: HISTORY#{timestamp}#{history_id}
```

**Attributes:**
```json
{
  "PK": "USER#user-uuid-123",
  "SK": "HISTORY#2025-01-15T14:30:00Z#history-456",
  "EntityType": "SearchHistory",
  "HistoryId": "history-456",
  "UserId": "user-uuid-123",
  "UserIdentifier": "user@example.com",
  "ProblemPK": "PROBLEM#baekjoon#1000",
  "ProblemId": "internal-id-789",
  "Platform": "baekjoon",
  "ProblemNumber": "1000",
  "ProblemTitle": "A+B",
  "Language": "python",
  "Code": "a, b = map(int, input().split())\nprint(a + b)",
  "ResultSummary": {"passed": 95, "failed": 5},
  "PassedCount": 95,
  "FailedCount": 5,
  "TotalCount": 100,
  "IsCodePublic": true,
  "TestResults": [
    {
      "test_case_id": "abc123",
      "status": "passed",
      "actual_output": "3",
      "execution_time": 0.002
    }
  ],
  "Hints": ["Check edge cases", "Consider integer overflow"],
  "Metadata": {
    "execution_time_ms": 150,
    "memory_usage_mb": 25
  },
  "CreatedAt": "2025-01-15T14:30:00Z",
  "GSI1PK": "PUBLIC#true",
  "GSI1SK": "2025-01-15T14:30:00Z",
  "GSI2PK": "PLATFORM#baekjoon",
  "GSI2SK": "2025-01-15T14:30:00Z",
  "GSI3PK": "LANGUAGE#python",
  "GSI3SK": "2025-01-15T14:30:00Z"
}
```

**Why this design:**
- PK by user enables efficient user history queries
- SK with timestamp provides reverse chronological ordering
- Denormalized platform/problem fields optimize list queries (matches current design)
- GSI1 enables public history feed
- GSI2/GSI3 enable filtering by platform/language

#### 4. UsageLog Entity

```
PK: USER#{user_id}
SK: USAGE#{date}#{action}#{timestamp}#{uuid}
```

**Attributes:**
```json
{
  "PK": "USER#user-uuid-123",
  "SK": "USAGE#2025-01-15#hint#14:30:00Z#log-789",
  "EntityType": "UsageLog",
  "LogId": "log-789",
  "UserId": "user-uuid-123",
  "Action": "hint",
  "ProblemId": "internal-id-789",
  "ProblemPK": "PROBLEM#baekjoon#1000",
  "Metadata": {
    "history_id": "history-456",
    "task_id": "celery-task-xyz"
  },
  "CreatedAt": "2025-01-15T14:30:00Z",
  "TTL": 1737849600
}
```

**Why this design:**
- PK by user groups all usage logs
- SK with date prefix enables efficient daily range queries
- Action in SK allows filtering by hint/execution
- Query pattern: `Query(PK="USER#uuid", SK between "USAGE#2025-01-15#" and "USAGE#2025-01-15#\uffff")`
- TTL set to delete logs after 90 days (cost optimization)

#### 5. ScriptGenerationJob Entity

```
PK: JOB#{job_id}
SK: METADATA
```

**Attributes:**
```json
{
  "PK": "JOB#job-123",
  "SK": "METADATA",
  "EntityType": "ScriptGenerationJob",
  "JobId": "job-123",
  "Platform": "baekjoon",
  "ProblemId": "1000",
  "Title": "A+B",
  "ProblemUrl": "https://www.acmicpc.net/problem/1000",
  "Tags": ["math", "implementation"],
  "SolutionCode": "...",
  "Language": "python",
  "Constraints": "1 <= a, b <= 10",
  "JobType": "script_generation",
  "Status": "COMPLETED",
  "CeleryTaskId": "celery-task-xyz",
  "GeneratorCode": "def generate_test_cases(n): ...",
  "ErrorMessage": null,
  "CreatedAt": "2025-01-15T10:00:00Z",
  "UpdatedAt": "2025-01-15T10:05:00Z",
  "GSI1PK": "JOBTYPE#script_generation",
  "GSI1SK": "2025-01-15T10:00:00Z",
  "GSI2PK": "STATUS#COMPLETED",
  "GSI2SK": "2025-01-15T10:05:00Z",
  "GSI3PK": "TASK#{celery_task_id}",
  "GSI3SK": "METADATA"
}
```

**Why this design:**
- Direct access by job ID
- GSI1 enables listing by job type
- GSI2 enables listing by status
- GSI3 enables lookup by Celery task ID

---

### Global Secondary Indexes (GSI) for Main Table

#### GSI1: Entity Type + Time Index
```
PK: GSI1PK
SK: GSI1SK
Projection: ALL
```

**Use cases:**
- List all completed problems by time
- List public search history feed
- List jobs by type

**Example queries:**
- Problems by platform: `Query(GSI1PK="PLATFORM#baekjoon", GSI1SK descending)`
- Public history: `Query(GSI1PK="PUBLIC#true", GSI1SK descending)`
- Jobs by type: `Query(GSI1PK="JOBTYPE#script_generation", GSI1SK descending)`

#### GSI2: Secondary Filter + Time Index
```
PK: GSI2PK
SK: GSI2SK
Projection: ALL
```

**Use cases:**
- List completed/draft problems
- Filter history by platform
- Filter jobs by status

**Example queries:**
- Completed problems: `Query(GSI2PK="COMPLETED#true", GSI2SK descending)`
- History by platform: `Query(GSI2PK="PLATFORM#baekjoon", GSI2SK descending)`
- Jobs by status: `Query(GSI2PK="STATUS#PENDING", GSI2SK descending)`

#### GSI3: Tertiary Filter + Time Index OR Lookup Index
```
PK: GSI3PK
SK: GSI3SK
Projection: ALL
```

**Use cases:**
- Filter problems by language
- Filter history by language
- Lookup job by Celery task ID

**Example queries:**
- Problems by language: `Query(GSI3PK="LANGUAGE#python", GSI3SK descending)`
- History by language: `Query(GSI3PK="LANGUAGE#python", GSI3SK descending)`
- Job by task: `Query(GSI3PK="TASK#celery-task-xyz")`

---

## Table 2: AlgoItny-Users

### Primary Key Structure

```
PK: USER#{email}
SK: METADATA
```

### Attributes
```json
{
  "PK": "USER#user@example.com",
  "SK": "METADATA",
  "EntityType": "User",
  "UserId": "user-uuid-123",
  "Email": "user@example.com",
  "Name": "John Doe",
  "Picture": "https://lh3.googleusercontent.com/...",
  "GoogleId": "google-oauth-id-123",
  "IsActive": true,
  "IsStaff": false,
  "IsSuperuser": false,
  "PasswordHash": "hashed-password",
  "SubscriptionPlanId": "plan-uuid-456",
  "SubscriptionPlanName": "Pro",
  "CreatedAt": "2025-01-01T00:00:00Z",
  "UpdatedAt": "2025-01-15T10:00:00Z",
  "LastLogin": "2025-01-15T10:00:00Z",
  "GSI1PK": "GOOGLEID#{google_id}",
  "GSI1SK": "METADATA",
  "GSI2PK": "PLAN#{subscription_plan_id}",
  "GSI2SK": "2025-01-01T00:00:00Z",
  "GSI3PK": "USERID#{user_id}",
  "GSI3SK": "METADATA"
}
```

### GSIs for Users Table

#### GSI1: Google ID Lookup
```
PK: GSI1PK (GOOGLEID#{google_id})
SK: GSI1SK
Projection: ALL
```
**Use case:** OAuth login by Google ID

#### GSI2: Plan Membership
```
PK: GSI2PK (PLAN#{plan_id})
SK: GSI2SK (CreatedAt)
Projection: ALL
```
**Use case:** List users by subscription plan (admin)

#### GSI3: User ID Lookup
```
PK: GSI3PK (USERID#{user_id})
SK: GSI3SK
Projection: ALL
```
**Use case:** Lookup user by internal UUID (for foreign key relationships)

---

## Table 3: AlgoItny-Plans

### Primary Key Structure

```
PK: PLAN#{plan_name}
SK: METADATA
```

### Attributes
```json
{
  "PK": "PLAN#Pro",
  "SK": "METADATA",
  "EntityType": "SubscriptionPlan",
  "PlanId": "plan-uuid-456",
  "Name": "Pro",
  "Description": "Professional plan with advanced features",
  "MaxHintsPerDay": 20,
  "MaxExecutionsPerDay": 500,
  "MaxProblems": -1,
  "CanViewAllProblems": true,
  "CanRegisterProblems": true,
  "IsActive": true,
  "CreatedAt": "2025-01-01T00:00:00Z",
  "UpdatedAt": "2025-01-15T10:00:00Z",
  "GSI1PK": "ACTIVE#true",
  "GSI1SK": "Pro"
}
```

### GSI for Plans Table

#### GSI1: Active Plans
```
PK: GSI1PK (ACTIVE#{is_active})
SK: GSI1SK (Name)
Projection: ALL
```
**Use case:** List active plans for user selection

---

## Migration from Django Models

### Field Mapping

#### User Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | UserId | UUID instead of auto-increment |
| email | Email (PK) | Use email as partition key |
| name | Name | Direct mapping |
| picture | Picture | Direct mapping |
| google_id | GoogleId + GSI1PK | Indexed for OAuth lookup |
| is_active | IsActive | Direct mapping |
| is_staff | IsStaff | Direct mapping |
| created_at | CreatedAt | ISO 8601 string |
| updated_at | UpdatedAt | ISO 8601 string |
| subscription_plan | SubscriptionPlanId + SubscriptionPlanName | Denormalized for efficiency |

#### Problem Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | InternalId | Maintain compatibility |
| platform | Platform (in PK) | Part of composite key |
| problem_id | ProblemId (in PK) | Part of composite key |
| title | Title | Direct mapping |
| problem_url | ProblemUrl | Direct mapping |
| tags | Tags | JSON list |
| solution_code | SolutionCode | Direct mapping |
| language | Language + GSI3PK | Indexed for filtering |
| constraints | Constraints | Direct mapping |
| is_completed | IsCompleted + GSI2PK | Indexed for filtering |
| is_deleted | IsDeleted | Soft delete flag |
| deleted_at | DeletedAt | ISO 8601 string |
| deleted_reason | DeletedReason | Direct mapping |
| metadata | Metadata | JSON object |
| created_at | CreatedAt + GSI1SK | Indexed for sorting |

#### TestCase Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | TestCaseId | UUID |
| problem (FK) | PK | Parent problem's PK |
| input | Input | Direct mapping |
| output | Output | Direct mapping |
| created_at | CreatedAt (in SK) | Part of sort key |

#### SearchHistory Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | HistoryId | UUID |
| user (FK) | UserId (in PK) | User's UUID |
| user_identifier | UserIdentifier | Direct mapping |
| problem (FK) | ProblemPK + ProblemId | Denormalized reference |
| platform | Platform + GSI2PK | Denormalized for performance |
| problem_number | ProblemNumber | Denormalized |
| problem_title | ProblemTitle | Denormalized |
| language | Language + GSI3PK | Indexed for filtering |
| code | Code | Direct mapping |
| result_summary | ResultSummary | JSON object |
| passed_count | PassedCount | Direct mapping |
| failed_count | FailedCount | Direct mapping |
| total_count | TotalCount | Direct mapping |
| is_code_public | IsCodePublic + GSI1PK | Indexed for public feed |
| test_results | TestResults | JSON array |
| hints | Hints | JSON array |
| metadata | Metadata | JSON object |
| created_at | CreatedAt (in SK) | Part of sort key + GSI sorting |

#### UsageLog Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | LogId | UUID |
| user (FK) | UserId (in PK) | User's UUID |
| action | Action (in SK) | Part of sort key |
| problem (FK) | ProblemId + ProblemPK | Optional reference |
| metadata | Metadata | JSON object |
| created_at | CreatedAt (in SK) | Part of sort key for daily queries |
| N/A | TTL | Auto-delete after 90 days |

#### ScriptGenerationJob Model
| Django Field | DynamoDB Attribute | Notes |
|--------------|-------------------|--------|
| id | JobId | UUID |
| platform | Platform | Direct mapping |
| problem_id | ProblemId | Direct mapping |
| title | Title | Direct mapping |
| problem_url | ProblemUrl | Direct mapping |
| tags | Tags | JSON list |
| solution_code | SolutionCode | Direct mapping |
| language | Language | Direct mapping |
| constraints | Constraints | Direct mapping |
| job_type | JobType + GSI1PK | Indexed for filtering |
| status | Status + GSI2PK | Indexed for filtering |
| celery_task_id | CeleryTaskId + GSI3PK | Indexed for lookup |
| generator_code | GeneratorCode | Direct mapping |
| error_message | ErrorMessage | Direct mapping |
| created_at | CreatedAt + GSI1SK/GSI2SK | Indexed for sorting |
| updated_at | UpdatedAt | Direct mapping |

---

## Query Pattern Implementation

### High-Frequency Queries

#### 1. Get Problem by Platform + ProblemId
```python
# Django ORM
problem = Problem.objects.get(platform='baekjoon', problem_id='1000')

# DynamoDB
response = table.get_item(
    Key={
        'PK': 'PROBLEM#baekjoon#1000',
        'SK': 'METADATA'
    }
)
```
**Performance:** Single-item read (1 RCU), sub-10ms latency

#### 2. Get Problem with Test Cases
```python
# Django ORM (N+1 without prefetch)
problem = Problem.objects.prefetch_related('test_cases').get(id=1)
test_cases = problem.test_cases.all()

# DynamoDB (Single query)
response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': 'PROBLEM#baekjoon#1000',
        ':sk': 'TESTCASE#'
    }
)
# First item is problem (SK=METADATA), rest are test cases
```
**Performance:** Single query fetches problem + all test cases (scales with test count)

#### 3. List Completed Problems by Platform
```python
# Django ORM
problems = Problem.objects.filter(
    platform='baekjoon',
    is_completed=True
).order_by('-created_at')

# DynamoDB (GSI1)
response = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'PLATFORM#baekjoon'
    },
    ScanIndexForward=False  # Descending by time
)
```
**Performance:** GSI query, efficient with pagination

#### 4. Get User's Search History
```python
# Django ORM
history = SearchHistory.objects.filter(user=user).order_by('-created_at')[:20]

# DynamoDB
response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
    ExpressionAttributeValues={
        ':pk': f'USER#{user_id}',
        ':sk': 'HISTORY#'
    },
    ScanIndexForward=False,
    Limit=20
)
```
**Performance:** Highly efficient, naturally ordered by time

#### 5. Check Daily Usage (Rate Limiting)
```python
# Django ORM
today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
count = UsageLog.objects.filter(
    user=user,
    action='hint',
    created_at__gte=today_start
).count()

# DynamoDB
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
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
**Performance:** Extremely fast, only counts without reading data

#### 6. Public Search History Feed
```python
# Django ORM
history = SearchHistory.objects.filter(
    is_code_public=True
).order_by('-created_at')[:50]

# DynamoDB (GSI1)
response = table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'PUBLIC#true'
    },
    ScanIndexForward=False,
    Limit=50
)
```
**Performance:** GSI query, efficient pagination

#### 7. User Login by Email
```python
# Django ORM
user = User.objects.get(email='user@example.com')

# DynamoDB (Users Table)
response = users_table.get_item(
    Key={
        'PK': 'USER#user@example.com',
        'SK': 'METADATA'
    }
)
```
**Performance:** Single-item read, sub-10ms

#### 8. User Login by Google ID
```python
# Django ORM
user = User.objects.get(google_id='google-oauth-123')

# DynamoDB (Users Table, GSI1)
response = users_table.query(
    IndexName='GSI1',
    KeyConditionExpression='GSI1PK = :pk',
    ExpressionAttributeValues={
        ':pk': 'GOOGLEID#google-oauth-123'
    }
)
```
**Performance:** GSI query, sub-10ms for OAuth

---

## Capacity Planning & Cost Optimization

### Capacity Mode Recommendations

#### AlgoItny-Main Table
- **Mode:** Provisioned capacity with Auto Scaling
- **Rationale:** Predictable traffic patterns, cost-effective for steady load
- **Initial Settings:**
  - Read: 25 RCU (baseline) → 500 RCU (burst)
  - Write: 10 WCU (baseline) → 100 WCU (burst)
  - Auto-scaling target: 70% utilization

#### AlgoItny-Users Table
- **Mode:** On-Demand
- **Rationale:** Low frequency, unpredictable admin operations
- **Expected Usage:** <100 reads/writes per day

#### AlgoItny-Plans Table
- **Mode:** On-Demand
- **Rationale:** Very low frequency, read-heavy
- **Expected Usage:** <50 reads/writes per day

### Cost Optimization Strategies

#### 1. TTL (Time-To-Live) for UsageLog
- **Purpose:** Auto-delete usage logs after 90 days
- **Impact:** Reduces storage costs by 90% for time-series data
- **Implementation:** Set TTL attribute to Unix timestamp (created_at + 90 days)

#### 2. Minimal Index Projection
- **Strategy:** Use KEYS_ONLY projection for indexes where full item isn't needed
- **Impact:** Reduces storage costs for GSIs by 60-80%
- **Consideration:** Current design uses ALL projection for flexibility; optimize after traffic analysis

#### 3. Item Size Optimization
- **Problem:** Keep all items under 4KB to minimize RCU costs
- **Strategy:**
  - Use compression for large code/test case fields
  - Move large solution code to S3, store reference in DynamoDB
  - Paginate large test case lists

#### 4. Efficient Batch Operations
- **Strategy:** Use BatchGetItem and BatchWriteItem for bulk operations
- **Impact:** 50% cost reduction for bulk reads/writes
- **Use cases:** Problem list fetches, test case creation

#### 5. Consistent Reads vs Eventually Consistent
- **Strategy:** Use eventually consistent reads for non-critical queries
- **Impact:** 50% RCU cost reduction
- **Application:** History feeds, problem lists, analytics

#### 6. Sparse Indexes
- **Strategy:** Only populate GSI attributes when needed
- **Example:** GSI1PK only set for public history (IsCodePublic=true)
- **Impact:** Reduces GSI storage costs by only indexing relevant items

### Estimated Monthly Costs (1000 DAU)

**Assumptions:**
- 1000 daily active users
- 50 problem searches per user per day
- 20 code executions per user per day
- 5 history views per user per day

**Main Table:**
```
Reads:  1000 users × 75 reads/day × 30 days = 2.25M reads/month
Writes: 1000 users × 20 writes/day × 30 days = 600K writes/month

Provisioned Capacity:
- Read: 50 RCU (average) = $23.40/month
- Write: 20 WCU (average) = $9.36/month
- Storage: 10 GB = $2.50/month
- GSIs (3 × 50 RCU + 3 × 20 WCU) = $98.28/month

Total Main Table: ~$133/month
```

**Users Table:**
```
On-Demand:
- Reads: ~3K/month = $0.75/month
- Writes: ~1K/month = $0.25/month
- Storage: 1 GB = $0.25/month

Total Users Table: ~$1.25/month
```

**Plans Table:**
```
On-Demand:
- Reads: ~500/month = $0.13/month
- Writes: ~50/month = $0.01/month
- Storage: 0.1 GB = $0.03/month

Total Plans Table: ~$0.17/month
```

**Grand Total: ~$135/month** (vs ~$50-100/month for RDS, but with better scalability)

---

## Migration Strategy

### Phase 1: Dual-Write (2-4 weeks)
1. Deploy DynamoDB tables alongside existing PostgreSQL/MySQL
2. Implement dual-write logic: write to both databases
3. Use feature flags to gradually enable DynamoDB reads for non-critical endpoints
4. Monitor data consistency and performance metrics

### Phase 2: Data Migration (1-2 weeks)
1. Export existing data from PostgreSQL/MySQL
2. Transform data to DynamoDB format (handle ID mapping, denormalization)
3. Bulk import using BatchWriteItem or DynamoDB Import from S3
4. Verify data integrity with automated tests

### Phase 3: Read Migration (2-3 weeks)
1. Gradually shift read traffic to DynamoDB (10% → 50% → 100%)
2. Monitor latency, error rates, and consistency
3. Optimize queries based on CloudWatch metrics
4. Rollback capability at each stage

### Phase 4: Write Migration (1-2 weeks)
1. Switch all writes to DynamoDB
2. Maintain PostgreSQL/MySQL as read-only backup for 30 days
3. Stop dual-write logic

### Phase 5: Decommission (1 week)
1. Export PostgreSQL/MySQL data for archival
2. Shut down old database
3. Remove dual-write code

**Total Timeline: 7-12 weeks**

---

## Potential Challenges & Trade-offs

### Challenge 1: Complex Queries
**Issue:** Django ORM's complex filtering (multiple ANDs, ORs) not directly supported
**Solution:**
- Redesign queries to leverage GSIs
- Use FilterExpression for secondary filters (post-query filtering)
- Accept some queries require scanning (use Scan with parallel processing)
- Example: "Problems by platform AND language" → Query GSI1 by platform, filter by language

**Trade-off:** Some complex admin queries may be slower

### Challenge 2: Transactions
**Issue:** DynamoDB transactions limited to 100 items, higher latency
**Current Usage:** Problem + TestCase creation (1 problem + N test cases)
**Solution:**
- Use transactional writes for problem + metadata
- Use BatchWriteItem for test cases (eventual consistency acceptable)
- Implement idempotency tokens for retry safety

**Trade-off:** No ACID guarantees across all items

### Challenge 3: Aggregations
**Issue:** No native SUM, AVG, COUNT aggregations like SQL
**Current Usage:** User stats (count by platform, language)
**Solution:**
- Use DynamoDB Streams + Lambda for real-time aggregations
- Store pre-aggregated counts in User item attributes
- Update aggregates on write (increment counters)
- For admin analytics, use Athena queries on DynamoDB exports

**Trade-off:** Aggregations require additional infrastructure

### Challenge 4: Full-Text Search
**Issue:** DynamoDB doesn't support full-text search (LIKE '%term%')
**Current Usage:** Problem title/description search
**Solution:**
- Use Amazon OpenSearch Service for search functionality
- Sync data using DynamoDB Streams → Lambda → OpenSearch
- Keep DynamoDB as source of truth, OpenSearch as search index

**Trade-off:** Additional service dependency and cost (~$30/month for small instance)

### Challenge 5: Schema Evolution
**Issue:** No native migrations like Django
**Current Usage:** Django migrations add/modify fields
**Solution:**
- DynamoDB is schema-less (flexible)
- Handle missing attributes in application code (default values)
- Use versioning attribute for backward compatibility
- Batch update items when needed (background job)

**Trade-off:** More application-level logic for schema handling

### Challenge 6: Testing
**Issue:** Unit tests currently use SQLite in-memory
**Current Usage:** Django test fixtures with relational data
**Solution:**
- Use DynamoDB Local for development/testing
- Use Moto library for Python mocking
- Create test fixtures in DynamoDB format
- Implement helper methods for test data setup

**Trade-off:** More complex test setup

### Challenge 7: Soft Deletes with Indexes
**Issue:** Soft-deleted problems still consume GSI storage
**Current Implementation:** is_deleted flag
**Solution:**
- Remove GSI attributes on soft delete (sparse indexes)
- Set IsDeleted=true, remove GSI1PK/GSI2PK/GSI3PK
- Deleted items not returned in GSI queries
- Direct PK queries still retrieve deleted items (audit trail)

**Trade-off:** Update requires more write logic

---

## Security Considerations

### Access Control
- **IAM Policies:** Separate roles for read, write, admin operations
- **Fine-grained Access:** Use IAM condition keys to restrict access
  - Users can only query their own PK (USER#{user_id})
  - Admins can query all PKs
- **Encryption:** Enable encryption at rest (AWS managed keys)
- **VPC Endpoints:** Use VPC endpoints to avoid internet egress

### Data Privacy
- **PII Handling:** Email in Users table (encrypted at rest)
- **Code Privacy:** Respect is_code_public flag in SearchHistory
- **Audit Logging:** Enable CloudTrail for all table operations
- **Compliance:** GDPR right to erasure → delete all items with PK=USER#{user_id}

---

## Monitoring & Observability

### Key Metrics to Monitor

1. **Performance Metrics:**
   - Read/Write latency (p50, p99)
   - Consumed capacity vs provisioned capacity
   - Throttled requests
   - Error rates (4xx, 5xx)

2. **Cost Metrics:**
   - RCU/WCU consumption
   - Storage usage
   - GSI storage vs base table storage

3. **Application Metrics:**
   - Query execution time
   - Cache hit rates
   - Data consistency checks

### CloudWatch Alarms

1. **High Latency:** p99 latency > 100ms → scale up
2. **Throttling:** ThrottledRequests > 10/min → scale up
3. **High Consumption:** Consumed capacity > 80% → investigate hot partitions
4. **Cost Spike:** Daily cost > $10 → alert admin

### DynamoDB Best Practices

1. **Hot Partition Avoidance:**
   - Monitor CloudWatch Contributor Insights
   - Ensure even distribution of user IDs
   - Use random suffixes for high-write items if needed

2. **Connection Pooling:**
   - Reuse boto3 client instances
   - Use connection pooling in application

3. **Exponential Backoff:**
   - Implement retry logic with exponential backoff
   - Use boto3's built-in retry config

---

## Recommended DynamoDB SDK Patterns

### Python (Boto3) Examples

#### 1. Get Problem with Test Cases
```python
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('AlgoItny-Main')

def get_problem_with_test_cases(platform, problem_id):
    pk = f'PROBLEM#{platform}#{problem_id}'

    response = table.query(
        KeyConditionExpression=Key('PK').eq(pk)
    )

    items = response['Items']
    problem = next((item for item in items if item['SK'] == 'METADATA'), None)
    test_cases = [item for item in items if item['SK'].startswith('TESTCASE#')]

    return {
        'problem': problem,
        'test_cases': sorted(test_cases, key=lambda x: x['SK'])
    }
```

#### 2. Create Problem with Test Cases
```python
def create_problem_with_test_cases(problem_data, test_case_inputs):
    pk = f"PROBLEM#{problem_data['platform']}#{problem_data['problem_id']}"
    timestamp = datetime.utcnow().isoformat()

    with table.batch_writer() as batch:
        # Write problem metadata
        batch.put_item(Item={
            'PK': pk,
            'SK': 'METADATA',
            'EntityType': 'Problem',
            'Platform': problem_data['platform'],
            'ProblemId': problem_data['problem_id'],
            'Title': problem_data['title'],
            'IsCompleted': True,
            'CreatedAt': timestamp,
            'GSI1PK': f"PLATFORM#{problem_data['platform']}",
            'GSI1SK': timestamp,
            'GSI2PK': 'COMPLETED#true',
            'GSI2SK': timestamp,
        })

        # Write test cases
        for test_case in test_case_inputs:
            batch.put_item(Item={
                'PK': pk,
                'SK': f"TESTCASE#{timestamp}#{uuid.uuid4()}",
                'EntityType': 'TestCase',
                'Input': test_case['input'],
                'Output': test_case['output'],
                'CreatedAt': timestamp,
            })
```

#### 3. Check Daily Usage (Rate Limiting)
```python
def check_daily_usage(user_id, action):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    pk = f'USER#{user_id}'
    sk_prefix = f'USAGE#{today}#{action}#'

    response = table.query(
        KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix),
        Select='COUNT'
    )

    return response['Count']
```

#### 4. Get Public History Feed with Pagination
```python
def get_public_history(limit=20, last_key=None):
    query_params = {
        'IndexName': 'GSI1',
        'KeyConditionExpression': Key('GSI1PK').eq('PUBLIC#true'),
        'ScanIndexForward': False,
        'Limit': limit,
    }

    if last_key:
        query_params['ExclusiveStartKey'] = last_key

    response = table.query(**query_params)

    return {
        'items': response['Items'],
        'last_key': response.get('LastEvaluatedKey'),
        'has_more': 'LastEvaluatedKey' in response
    }
```

---

## Alternative Approaches Considered

### Alternative 1: Fully Single-Table Design (All Entities in One Table)
**Approach:** Include User and SubscriptionPlan in main table

**Pros:**
- Single table to manage
- Potential cost savings (fewer tables)

**Cons:**
- Security complexity (mixing user auth with application data)
- Hot partition risk (users accessed more frequently)
- Harder to implement fine-grained IAM policies
- Complicates backup/restore strategies

**Decision:** Rejected in favor of separate Users table for cleaner architecture

### Alternative 2: Multiple Tables (One Per Entity)
**Approach:** Separate table for each entity (Problems, TestCases, SearchHistory, etc.)

**Pros:**
- Familiar relational-like structure
- Easier migration from Django models
- Clear separation of concerns

**Cons:**
- Higher costs (more tables, more GSIs)
- Complex joins (multiple queries for related data)
- Doesn't leverage DynamoDB's strengths (hierarchical data)
- More expensive RCU/WCU consumption

**Decision:** Rejected in favor of hybrid approach

### Alternative 3: Relational Database Replacement (Aurora Serverless)
**Approach:** Keep PostgreSQL but use Aurora Serverless for auto-scaling

**Pros:**
- No application changes needed
- Keep Django ORM
- ACID transactions
- Complex queries supported

**Cons:**
- Cold start latency (2-5 seconds)
- Still has connection pooling limits
- Higher costs at scale ($50-500/month)
- Not as globally scalable as DynamoDB

**Decision:** Out of scope (you requested DynamoDB design)

---

## Next Steps & Recommendations

### Immediate Actions (Before Migration)

1. **Traffic Analysis:**
   - Enable detailed PostgreSQL query logging
   - Identify most frequent queries and their patterns
   - Measure current p50/p99 latencies
   - Establish baseline metrics for comparison

2. **Prototype Critical Queries:**
   - Build proof-of-concept for top 10 queries in DynamoDB
   - Benchmark performance vs PostgreSQL
   - Validate data model assumptions

3. **Design Review:**
   - Review this design with django-backend-architect
   - Identify any missing access patterns
   - Validate GSI requirements
   - Confirm capacity estimates

### During Migration

1. **Implement Abstraction Layer:**
   - Create repository pattern to abstract database operations
   - Makes switching between PostgreSQL and DynamoDB easier
   - Enables gradual rollout

2. **Add OpenSearch for Search:**
   - Required for problem title/description full-text search
   - Set up DynamoDB Streams → Lambda → OpenSearch pipeline

3. **Implement Caching Strategy:**
   - Use ElastiCache (Redis) for hot data
   - Cache problem details, user plans, test cases
   - Reduces DynamoDB read costs by 60-80%

4. **Set Up Monitoring:**
   - CloudWatch dashboards for all tables
   - Custom metrics for application-level latency
   - Cost tracking by table and operation

### Post-Migration

1. **Optimize Based on Metrics:**
   - Adjust provisioned capacity based on actual usage
   - Identify hot partitions and optimize
   - Convert indexes to KEYS_ONLY projection where possible

2. **Implement DynamoDB Streams:**
   - Real-time aggregations for user stats
   - Audit logging for compliance
   - Data sync to analytics warehouse

3. **Consider Global Tables:**
   - If serving international users
   - Multi-region replication for low latency
   - Disaster recovery

---

## Conclusion

This DynamoDB design provides a scalable, cost-effective solution for the AlgoItny platform with the following key benefits:

**Performance:**
- Sub-10ms latency for single-item reads
- Efficient pagination for large datasets
- Optimized queries for all hot-path access patterns

**Scalability:**
- Handles 10x traffic growth without architecture changes
- Auto-scaling for unpredictable loads
- No connection pooling limits

**Cost:**
- Estimated $135/month for 1000 DAU (competitive with RDS)
- TTL-based auto-deletion reduces storage costs
- On-demand pricing for low-frequency tables

**Maintainability:**
- Clear entity separation with composite keys
- Sparse indexes reduce unnecessary storage
- Schema-less design simplifies future changes

**Trade-offs to Accept:**
- Complex queries require application-level logic or scanning
- No native full-text search (requires OpenSearch)
- Aggregations require additional infrastructure
- More complex testing setup

The hybrid approach (single table for hot data, separate tables for admin) strikes the right balance between DynamoDB best practices and practical migration complexity. This design supports all current Django access patterns while positioning the platform for future growth.

**Recommendation:** Proceed with Phase 1 (Dual-Write) after design review and prototype validation.

---

## Appendix: Key Design Principles Applied

1. **Store Data the Way You Access It:** Primary keys align with most common query patterns
2. **Denormalization for Performance:** Platform, problem title in SearchHistory for fast lists
3. **Hierarchical Data with Sort Keys:** Problem → TestCases in single query
4. **Sparse Indexes:** Only index items that need to be queried (public history, active plans)
5. **Time-Series Optimization:** UsageLog with date in sort key for efficient daily queries
6. **Composite Key Strategy:** Encode entity type and ID in keys for flexible querying
7. **GSI Overloading:** Reuse GSI1/GSI2/GSI3 for multiple entity types with different filters

---

**Document Version:** 1.0
**Last Updated:** 2025-01-15
**Author:** DynamoDB Architect Agent
**Status:** Ready for Review
