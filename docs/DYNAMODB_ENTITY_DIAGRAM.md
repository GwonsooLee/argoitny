# DynamoDB Entity Relationship Diagram

## Table Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         APPLICATION LAYER                                    │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Problems  │  │   Execute   │  │   History   │  │   Account   │       │
│  │   API       │  │   API       │  │   API       │  │   API       │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                 │                 │                 │              │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         DYNAMODB LAYER                                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                    AlgoItny-Main                              │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │          │
│  │  │  Problem    │  │ SearchHistory│  │  UsageLog   │          │          │
│  │  │  + TestCase │  │             │  │             │          │          │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │          │
│  │  ┌─────────────┐                                             │          │
│  │  │ ScriptGenJob│                                             │          │
│  │  └─────────────┘                                             │          │
│  │                                                               │          │
│  │  GSI1: Platform/Public/JobType + Time                        │          │
│  │  GSI2: Completed/Status + Time                               │          │
│  │  GSI3: Language/TaskID + Time                                │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                   AlgoItny-Users                              │          │
│  │  ┌─────────────┐                                             │          │
│  │  │    User     │                                             │          │
│  │  └─────────────┘                                             │          │
│  │                                                               │          │
│  │  GSI1: GoogleID Lookup                                       │          │
│  │  GSI2: Plan Membership                                       │          │
│  │  GSI3: UserID Lookup                                         │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                   AlgoItny-Plans                              │          │
│  │  ┌─────────────┐                                             │          │
│  │  │Subscription │                                             │          │
│  │  │    Plan     │                                             │          │
│  │  └─────────────┘                                             │          │
│  │                                                               │          │
│  │  GSI1: Active Plans                                          │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Entity Hierarchy in AlgoItny-Main Table

```
PROBLEM ENTITY
┌────────────────────────────────────────────────────────────────┐
│ PK: PROBLEM#{platform}#{problem_id}                            │
│ SK: METADATA                                                   │
├────────────────────────────────────────────────────────────────┤
│ • EntityType: Problem                                          │
│ • InternalId: uuid                                             │
│ • Platform, ProblemId, Title, Language                         │
│ • IsCompleted, IsDeleted                                       │
│ • Tags (JSON array), Metadata (JSON object)                    │
│ • CreatedAt, UpdatedAt                                         │
│ • GSI1PK: PLATFORM#{platform}                                  │
│ • GSI2PK: COMPLETED#{is_completed}                             │
│ • GSI3PK: LANGUAGE#{language}                                  │
└────────────────────────────────────────────────────────────────┘
         │
         │ 1:N relationship (same PK)
         ▼
┌────────────────────────────────────────────────────────────────┐
│ PK: PROBLEM#{platform}#{problem_id}                            │
│ SK: TESTCASE#{timestamp}#{uuid}                                │
├────────────────────────────────────────────────────────────────┤
│ • EntityType: TestCase                                         │
│ • TestCaseId: uuid                                             │
│ • Input (text), Output (text)                                  │
│ • CreatedAt                                                    │
└────────────────────────────────────────────────────────────────┘


USER ACTIVITY ENTITY
┌────────────────────────────────────────────────────────────────┐
│ PK: USER#{user_id}                                             │
│ SK: HISTORY#{timestamp}#{history_id}                           │
├────────────────────────────────────────────────────────────────┤
│ • EntityType: SearchHistory                                    │
│ • HistoryId: uuid                                              │
│ • UserId, UserIdentifier                                       │
│ • ProblemPK (reference), ProblemId                             │
│ • Platform, ProblemNumber, ProblemTitle (denormalized)         │
│ • Language, Code                                               │
│ • PassedCount, FailedCount, TotalCount                         │
│ • IsCodePublic                                                 │
│ • TestResults (JSON array), Hints (JSON array)                 │
│ • GSI1PK: PUBLIC#{is_public}                                   │
│ • GSI2PK: PLATFORM#{platform}                                  │
│ • GSI3PK: LANGUAGE#{language}                                  │
└────────────────────────────────────────────────────────────────┘


USAGE TRACKING ENTITY
┌────────────────────────────────────────────────────────────────┐
│ PK: USER#{user_id}                                             │
│ SK: USAGE#{date}#{action}#{timestamp}#{uuid}                   │
├────────────────────────────────────────────────────────────────┤
│ • EntityType: UsageLog                                         │
│ • LogId: uuid                                                  │
│ • UserId, Action (hint|execution)                              │
│ • ProblemId, ProblemPK (optional reference)                    │
│ • Metadata (JSON object)                                       │
│ • CreatedAt                                                    │
│ • TTL (auto-delete after 90 days)                              │
└────────────────────────────────────────────────────────────────┘


ASYNC JOB ENTITY
┌────────────────────────────────────────────────────────────────┐
│ PK: JOB#{job_id}                                               │
│ SK: METADATA                                                   │
├────────────────────────────────────────────────────────────────┤
│ • EntityType: ScriptGenerationJob                              │
│ • JobId: uuid                                                  │
│ • Platform, ProblemId, Title, Language                         │
│ • JobType, Status, CeleryTaskId                                │
│ • GeneratorCode (result), ErrorMessage                         │
│ • CreatedAt, UpdatedAt                                         │
│ • GSI1PK: JOBTYPE#{job_type}                                   │
│ • GSI2PK: STATUS#{status}                                      │
│ • GSI3PK: TASK#{celery_task_id}                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Access Pattern Map

### Map 1: Problem Queries

```
ACCESS PATTERN                        PRIMARY/GSI        KEY CONDITION
─────────────────────────────────────────────────────────────────────────
Get problem by platform+ID            PRIMARY            PK = PROBLEM#...
Get problem with test cases           PRIMARY            PK = PROBLEM#... & SK begins_with TESTCASE#
List problems by platform             GSI1               GSI1PK = PLATFORM#baekjoon
List completed problems               GSI2               GSI2PK = COMPLETED#true
List problems by language             GSI3               GSI3PK = LANGUAGE#python
Search problems by title              SCAN + Filter      (Use OpenSearch instead)
```

### Map 2: Search History Queries

```
ACCESS PATTERN                        PRIMARY/GSI        KEY CONDITION
─────────────────────────────────────────────────────────────────────────
Get user's history                    PRIMARY            PK = USER#{id} & SK begins_with HISTORY#
Get public history feed               GSI1               GSI1PK = PUBLIC#true
Filter history by platform            GSI2               GSI2PK = PLATFORM#baekjoon
Filter history by language            GSI3               GSI3PK = LANGUAGE#python
Get specific history item             PRIMARY            PK = USER#{id} & SK = HISTORY#{timestamp}#{id}
```

### Map 3: Usage & Rate Limiting Queries

```
ACCESS PATTERN                        PRIMARY/GSI        KEY CONDITION
─────────────────────────────────────────────────────────────────────────
Count today's hints                   PRIMARY            PK = USER#{id} & SK begins_with USAGE#{date}#hint#
Count today's executions              PRIMARY            PK = USER#{id} & SK begins_with USAGE#{date}#execution#
Get usage logs for date range         PRIMARY            PK = USER#{id} & SK BETWEEN USAGE#{start} AND USAGE#{end}
```

### Map 4: Job Queries

```
ACCESS PATTERN                        PRIMARY/GSI        KEY CONDITION
─────────────────────────────────────────────────────────────────────────
Get job by ID                         PRIMARY            PK = JOB#{id} & SK = METADATA
List jobs by type                     GSI1               GSI1PK = JOBTYPE#script_generation
List jobs by status                   GSI2               GSI2PK = STATUS#PENDING
Get job by Celery task ID             GSI3               GSI3PK = TASK#{celery_id}
```

### Map 5: User Queries

```
ACCESS PATTERN                        PRIMARY/GSI        KEY CONDITION (Users Table)
─────────────────────────────────────────────────────────────────────────
Get user by email                     PRIMARY            PK = USER#{email} & SK = METADATA
Get user by Google ID                 GSI1               GSI1PK = GOOGLEID#{google_id}
List users by plan                    GSI2               GSI2PK = PLAN#{plan_id}
Get user by internal ID               GSI3               GSI3PK = USERID#{uuid}
```

---

## Data Flow Diagrams

### Flow 1: Code Execution

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ POST /api/execute/
       │ {code, language, problem_id}
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend API (ExecuteCodeView)                                   │
│                                                                  │
│ 1. Check rate limit:                                            │
│    Query: PK=USER#{id}, SK begins_with USAGE#{today}#execution# │
│    Count items → Compare with limit                             │
│                                                                  │
│ 2. Get problem + test cases:                                    │
│    Query: PK=PROBLEM#{platform}#{problem_id}                    │
│    Returns: problem (SK=METADATA) + test cases (SK=TESTCASE#*)  │
│                                                                  │
│ 3. Start async execution task (Celery)                          │
│                                                                  │
│ 4. Log usage:                                                   │
│    Put: PK=USER#{id}, SK=USAGE#{today}#execution#{timestamp}#*  │
│                                                                  │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Celery Task (execute_code_task)                                 │
│                                                                  │
│ 1. Execute code against each test case                          │
│                                                                  │
│ 2. Save results to SearchHistory:                               │
│    Put: PK=USER#{id}, SK=HISTORY#{timestamp}#{history_id}       │
│    Attributes: Code, TestResults, PassedCount, FailedCount, etc. │
│    GSI1PK: PUBLIC#{is_public} (if public)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flow 2: Problem Registration

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ POST /api/register/generate-test-cases/
       │ {platform, problem_id, solution_code, language, constraints}
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend API (GenerateTestCasesView)                             │
│                                                                  │
│ 1. Create job:                                                  │
│    Put: PK=JOB#{job_id}, SK=METADATA                            │
│    Attributes: Platform, ProblemId, Language, Status=PENDING    │
│    GSI1PK: JOBTYPE#script_generation                            │
│    GSI2PK: STATUS#PENDING                                       │
│                                                                  │
│ 2. Start async task (Celery) → Returns job_id                  │
│                                                                  │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Celery Task (generate_script_task)                              │
│                                                                  │
│ 1. Update job status to PROCESSING                              │
│    Update: PK=JOB#{job_id}, SK=METADATA                         │
│    Set Status=PROCESSING, GSI2PK=STATUS#PROCESSING              │
│                                                                  │
│ 2. Call Gemini API to generate test case generator code         │
│                                                                  │
│ 3. Update job with results:                                     │
│    Update: PK=JOB#{job_id}, SK=METADATA                         │
│    Set Status=COMPLETED, GeneratorCode=..., GSI2PK=STATUS#...   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼ (User reviews and approves)
┌─────────────────────────────────────────────────────────────────┐
│ Backend API (SaveProblemView)                                   │
│                                                                  │
│ 1. Create problem:                                              │
│    Put: PK=PROBLEM#{platform}#{problem_id}, SK=METADATA         │
│    Attributes: Title, Language, IsCompleted=true                │
│    GSI1PK: PLATFORM#{platform}                                  │
│    GSI2PK: COMPLETED#true                                       │
│    GSI3PK: LANGUAGE#{language}                                  │
│                                                                  │
│ 2. Create test cases (batch write):                             │
│    BatchPut: Multiple items with                                │
│    PK=PROBLEM#{platform}#{problem_id}                           │
│    SK=TESTCASE#{timestamp}#{uuid}                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flow 3: Hint Generation

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ POST /api/history/{history_id}/hints/generate/
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend API (GenerateHintsView)                                 │
│                                                                  │
│ 1. Check rate limit:                                            │
│    Query: PK=USER#{id}, SK begins_with USAGE#{today}#hint#      │
│    Count items → Compare with limit                             │
│                                                                  │
│ 2. Get SearchHistory item:                                      │
│    GetItem: PK=USER#{id}, SK=HISTORY#{timestamp}#{history_id}   │
│    Check if hints already exist                                 │
│                                                                  │
│ 3. Start async task (Celery) if not exists                      │
│                                                                  │
│ 4. Log usage:                                                   │
│    Put: PK=USER#{id}, SK=USAGE#{today}#hint#{timestamp}#*       │
│                                                                  │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Celery Task (generate_hints_task)                               │
│                                                                  │
│ 1. Get SearchHistory with problem details                       │
│                                                                  │
│ 2. Call Gemini API to generate hints based on failed tests      │
│                                                                  │
│ 3. Update SearchHistory with hints:                             │
│    Update: PK=USER#{id}, SK=HISTORY#{timestamp}#{history_id}    │
│    Set Hints=[hint1, hint2, hint3]                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Index Strategy Visualization

### GSI1: Multi-Purpose Entity+Time Index

```
┌──────────────────────────────────────────────────────────────────┐
│                            GSI1                                   │
│                                                                   │
│  Partition Key: GSI1PK              Sort Key: GSI1SK             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐                                         │
│  │ PLATFORM#baekjoon   │ ─────► Problem entities sorted by time  │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ PLATFORM#codeforces │ ─────► Problem entities sorted by time  │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ PUBLIC#true         │ ─────► SearchHistory (public) by time   │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ JOBTYPE#script_gen  │ ─────► Jobs sorted by time              │
│  └─────────────────────┘                                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

SPARSE INDEX: Only items with GSI1PK populated are indexed
Cost Optimization: Reduces index storage by ~50%
```

### GSI2: Status/Completion Filter Index

```
┌──────────────────────────────────────────────────────────────────┐
│                            GSI2                                   │
│                                                                   │
│  Partition Key: GSI2PK              Sort Key: GSI2SK             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐                                         │
│  │ COMPLETED#true      │ ─────► Completed problems by time       │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ COMPLETED#false     │ ─────► Draft problems by time           │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ STATUS#PENDING      │ ─────► Pending jobs by time             │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ STATUS#PROCESSING   │ ─────► Processing jobs by time          │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ STATUS#COMPLETED    │ ─────► Completed jobs by time           │
│  └─────────────────────┘                                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### GSI3: Language/Lookup Index

```
┌──────────────────────────────────────────────────────────────────┐
│                            GSI3                                   │
│                                                                   │
│  Partition Key: GSI3PK              Sort Key: GSI3SK             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐                                         │
│  │ LANGUAGE#python     │ ─────► Problems/History by language     │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ LANGUAGE#cpp        │ ─────► Problems/History by language     │
│  └─────────────────────┘                                         │
│  ┌─────────────────────┐                                         │
│  │ TASK#celery-task-xyz│ ─────► Job lookup by task ID (exact)    │
│  └─────────────────────┘                                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

HYBRID USE: Both filtering (language) and exact lookup (task ID)
```

---

## Partition Strategy

### Main Table Partitioning

```
Hot Partitions (High Traffic):
┌────────────────────────────────────┐
│ USER#{user_id}                     │ ← Each user = separate partition
│   ├─ HISTORY#...                   │   Distributes load evenly
│   └─ USAGE#...                     │   No hot partition risk
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ PROBLEM#{platform}#{problem_id}    │ ← Each problem = separate partition
│   ├─ METADATA                      │   Distributes load
│   └─ TESTCASE#...                  │   Even with popular problems
└────────────────────────────────────┘


Cold Partitions (Low Traffic):
┌────────────────────────────────────┐
│ JOB#{job_id}                       │ ← Jobs accessed infrequently
└────────────────────────────────────┘

GSI Partitions (Read Distribution):
┌────────────────────────────────────┐
│ PLATFORM#baekjoon                  │ ← Can be hot if platform popular
│ PLATFORM#codeforces                │   Monitor with Contributor Insights
│ PLATFORM#leetcode                  │   Consider adding random suffix
└────────────────────────────────────┘
```

### Hot Partition Mitigation Strategies

```
IF GSI partition becomes hot (>1000 RCU/partition):

Strategy 1: Add Sharding Suffix
─────────────────────────────────
BEFORE: GSI1PK = PLATFORM#baekjoon
AFTER:  GSI1PK = PLATFORM#baekjoon#0
                 PLATFORM#baekjoon#1
                 PLATFORM#baekjoon#2
                 ...
Query: Scatter-gather across shards

Strategy 2: Use Caching
─────────────────────────────────
Cache popular problem lists in ElastiCache
TTL: 5 minutes for hot data
Reduces DynamoDB reads by 80%

Strategy 3: Use DynamoDB Accelerator (DAX)
─────────────────────────────────
In-memory cache (microsecond latency)
Cost: ~$0.16/hour for t3.small
Good for read-heavy workloads
```

---

## Denormalization Strategy

### What to Denormalize

```
SearchHistory Entity:
┌─────────────────────────────────────────────────────────────┐
│ DENORMALIZED FIELDS:                                        │
│                                                              │
│ • Platform          ← From Problem.platform                 │
│ • ProblemNumber     ← From Problem.problem_id               │
│ • ProblemTitle      ← From Problem.title                    │
│                                                              │
│ WHY DENORMALIZE?                                            │
│ • Enables filtering history by platform WITHOUT joining     │
│ • List view shows problem title without extra query         │
│ • Historical accuracy if problem details change             │
│ • Supports anonymous users (no FK constraint)               │
│                                                              │
│ TRADE-OFF:                                                  │
│ • Slight data redundancy                                    │
│ • Must update if problem title changes (rare)               │
└─────────────────────────────────────────────────────────────┘

User Entity:
┌─────────────────────────────────────────────────────────────┐
│ DENORMALIZED FIELDS:                                        │
│                                                              │
│ • SubscriptionPlanName  ← From SubscriptionPlan.name       │
│                                                              │
│ WHY DENORMALIZE?                                            │
│ • Avoids join for user profile display                      │
│ • Most common user query needs plan name                    │
│                                                              │
│ TRADE-OFF:                                                  │
│ • Must update if plan renamed (very rare)                   │
└─────────────────────────────────────────────────────────────┘
```

### What NOT to Denormalize

```
❌ Test Cases in Problem Record
   Reason: Large payload, fetched separately
   Solution: Store as child items (hierarchical)

❌ User Details in SearchHistory
   Reason: PII security concerns
   Solution: Store UserID reference, join when needed

❌ Full Problem in SearchHistory
   Reason: Unnecessary data duplication
   Solution: Store ProblemPK reference + minimal fields
```

---

## TTL (Time-To-Live) Strategy

```
UsageLog Entity:
┌─────────────────────────────────────────────────────────────┐
│ TTL Attribute: Expires                                      │
│ Value: CreatedAt + 90 days (Unix timestamp)                │
│                                                              │
│ Example:                                                     │
│ CreatedAt: 2025-01-15T00:00:00Z                             │
│ Expires: 1744761600 (2025-04-15 Unix timestamp)            │
│                                                              │
│ Auto-Deletion:                                              │
│ DynamoDB deletes item after TTL expires (within 48 hours)   │
│ No manual cleanup needed                                    │
│ No cost for deletion                                        │
│                                                              │
│ Storage Savings:                                            │
│ Without TTL: 1000 users × 50 logs/day × $0.25/GB = $∞      │
│ With TTL (90 days): 1000 × 50 × 90 / 10000 × 0.25 = $11.25│
└─────────────────────────────────────────────────────────────┘

Other Candidates for TTL:
• ScriptGenerationJob (delete after 30 days)
• SearchHistory for anonymous users (delete after 7 days)
• Old draft problems (delete after 180 days)
```

---

## Comparison: Django ORM vs DynamoDB

```
┌──────────────────────────────────────────────────────────────────────┐
│                     DJANGO ORM (PostgreSQL)                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Strengths:                                                          │
│  ✓ Familiar SQL-like queries                                        │
│  ✓ ACID transactions across all tables                              │
│  ✓ Complex joins and aggregations                                   │
│  ✓ Full-text search built-in                                        │
│  ✓ Easy migrations                                                  │
│                                                                       │
│  Weaknesses:                                                         │
│  ✗ Connection pooling limits (max ~100-200 connections)             │
│  ✗ Vertical scaling only (need bigger instance)                     │
│  ✗ N+1 query problems (need careful prefetch)                       │
│  ✗ Slow aggregations on large datasets                              │
│  ✗ Higher latency (20-100ms typical)                                │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         DYNAMODB                                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Strengths:                                                          │
│  ✓ Horizontal scaling (automatic)                                   │
│  ✓ No connection limits                                             │
│  ✓ Sub-10ms latency for key-based queries                           │
│  ✓ Hierarchical data in single query                                │
│  ✓ Auto-scaling and on-demand pricing                               │
│  ✓ TTL for automatic data expiration                                │
│  ✓ Global tables for multi-region                                   │
│                                                                       │
│  Weaknesses:                                                         │
│  ✗ No complex joins (must denormalize)                              │
│  ✗ No aggregations (need streams + Lambda)                          │
│  ✗ No full-text search (need OpenSearch)                            │
│  ✗ More complex data modeling                                       │
│  ✗ Application-level transactions                                   │
│  ✗ Scan operations expensive                                        │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## When to Use Each Table

```
AlgoItny-Main Table (Single Table Design):
──────────────────────────────────────────
USE FOR:
✓ High-frequency queries (problems, history, usage)
✓ User-specific data (history, usage logs)
✓ Time-series data (logs, history)
✓ Hierarchical relationships (problem → test cases)
✓ Data with multiple access patterns (platform, language filters)

DON'T USE FOR:
✗ Admin-only operations
✗ Infrequent configuration data
✗ User authentication (security isolation)


AlgoItny-Users Table (Separate Table):
───────────────────────────────────────
USE FOR:
✓ User authentication and profile
✓ Admin user management
✓ Security-sensitive operations
✓ Data requiring fine-grained IAM policies

DON'T USE FOR:
✗ User-generated content (use Main table)
✗ High-frequency usage tracking (use Main table)


AlgoItny-Plans Table (Separate Table):
───────────────────────────────────────
USE FOR:
✓ Subscription plan configuration
✓ Admin plan management
✓ Plan limits lookup

DON'T USE FOR:
✗ User-plan associations (store in Users table)
✗ Usage counting (use Main table)
```

---

**Last Updated:** 2025-01-15
**Version:** 1.0
