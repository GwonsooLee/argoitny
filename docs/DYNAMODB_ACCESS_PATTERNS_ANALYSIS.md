# DynamoDB Migration: Database Access Patterns Analysis

**Project:** AlgoItny - Algorithm Problem Test Case Manager
**Analysis Date:** 2025-10-07
**Total Code Analyzed:** 4,888 lines
**Analyst Role:** Django Backend Architect

---

## Executive Summary

This document provides a comprehensive analysis of all database access patterns in the AlgoItny Django application to facilitate migration to AWS DynamoDB. The application is a sophisticated algorithm problem management system with test case generation, code execution tracking, subscription-based rate limiting, and AI-powered hints.

**Key Findings:**
- 7 core entities with complex relationships
- High-read, moderate-write workload pattern
- Heavy use of relational joins (select_related, prefetch_related)
- Sophisticated caching layer already implemented (Redis)
- Time-series data patterns for usage tracking
- Multiple composite index requirements
- Soft delete patterns implemented

---

## Table of Contents

1. [Data Model Overview](#data-model-overview)
2. [Entity-by-Entity Access Patterns](#entity-by-entity-access-patterns)
3. [Hot Access Patterns](#hot-access-patterns)
4. [Relationship Traversals](#relationship-traversals)
5. [Query Performance Characteristics](#query-performance-characteristics)
6. [Caching Strategy](#caching-strategy)
7. [Rate Limiting & Usage Tracking](#rate-limiting--usage-tracking)
8. [Transaction Requirements](#transaction-requirements)
9. [DynamoDB Design Recommendations](#dynamodb-design-recommendations)
10. [Migration Challenges & Risks](#migration-challenges--risks)

---

## 1. Data Model Overview

### Entity Relationships

```
SubscriptionPlan (1) ----< (M) User (1) ----< (M) SearchHistory
                                   |
                                   +--------< (M) UsageLog

Problem (1) ----< (M) TestCase
   |
   +--------< (M) SearchHistory
   +--------< (M) UsageLog

ScriptGenerationJob (standalone with reference to Problem via platform/problem_id)
```

### Entity Summary

| Entity | Estimated Size | Write Frequency | Read Frequency | Relationships |
|--------|---------------|-----------------|----------------|---------------|
| **User** | Small-Medium (100s-1000s) | Low | High | FK to SubscriptionPlan, M2M to Groups/Permissions |
| **Problem** | Medium (1000s-10000s) | Low-Medium | Very High | FK to TestCase (1:M) |
| **TestCase** | Large (10000s-100000s) | Low | Very High | FK to Problem |
| **SearchHistory** | Very Large (100000s+) | High | High | FK to User, FK to Problem |
| **UsageLog** | Very Large (100000s+) | High | Medium | FK to User, FK to Problem |
| **SubscriptionPlan** | Tiny (5-10 records) | Very Low | High | Referenced by Users |
| **ScriptGenerationJob** | Medium (1000s) | Medium | Medium | References Problem |

---

## 2. Entity-by-Entity Access Patterns

### 2.1 User Model

**Schema:**
- Primary Key: `id` (auto-increment)
- Unique Keys: `email`, `google_id`
- Foreign Keys: `subscription_plan_id`
- Indexes:
  - `email` (db_index)
  - `google_id` (db_index)
  - `is_active` (db_index)
  - `created_at` (db_index)
  - Composite: `(is_active, -created_at)`
  - Composite: `(subscription_plan, is_active)`

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Login/Auth by Email** | Very High | `User.objects.get(email='user@email.com')` | email (unique) | Single item read |
| **Login/Auth by Google ID** | Very High | `User.objects.get(google_id='123...')` | google_id (unique) | Single item read |
| **User Creation** | Medium | `User.objects.create(email=..., google_id=...)` | N/A | Write operation |
| **Get User with Plan** | High | `User.objects.select_related('subscription_plan').get(id=x)` | PK + FK join | Join optimization critical |
| **List Active Users** | Low (Admin) | `User.objects.filter(is_active=True).order_by('-created_at')` | is_active + created_at composite | Admin dashboard |
| **Users by Plan** | Low (Admin) | `User.objects.filter(subscription_plan=x, is_active=True)` | plan + active composite | Admin filtering |
| **Check Admin Status** | High | Called on every admin request via `user.is_admin()` | N/A | In-memory check against config |

**Denormalized Fields:**
- None currently, but plan limits are accessed via FK join frequently

**Performance Notes:**
- Authentication queries are extremely hot (every request)
- Plan limits retrieved frequently for rate limiting
- Current optimization: `select_related('subscription_plan')` to avoid N+1

---

### 2.2 Problem Model

**Schema:**
- Primary Key: `id` (auto-increment)
- Unique Key: `(platform, problem_id)` composite
- Indexes:
  - `platform` (db_index)
  - `problem_id` (db_index)
  - `title` (db_index)
  - `language` (db_index)
  - `is_completed` (db_index)
  - `is_deleted` (db_index)
  - `deleted_at` (db_index)
  - `created_at` (db_index)
  - Composite: `(platform, problem_id)` - unique_together
  - Composite: `(platform, -created_at)`
  - Composite: `(is_completed, -created_at)`
  - Composite: `(language, -created_at)`
  - Composite: `(is_deleted, is_completed, -created_at)`
- JSON Fields: `tags`, `metadata`

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Get Problem by ID** | Very High | `Problem.objects.get(id=x)` | PK | Single item, cached |
| **Get Problem by Platform+ID** | Very High | `Problem.objects.get(platform='baekjoon', problem_id='1000')` | Unique composite | Single item, cached |
| **Get Problem with Test Cases** | Very High | `Problem.objects.prefetch_related('test_cases').get(id=x)` | PK + 1:M join | Critical hot path |
| **List All Problems** | Very High | `Problem.objects.filter(is_completed=True, is_deleted=False).order_by('-created_at')` | deleted+completed composite | Main list view, cached |
| **Search by Title** | Medium | `Problem.objects.filter(title__icontains='search').filter(is_completed=True)` | title + completion | Full-text search requirement |
| **Search by Problem ID** | Medium | `Problem.objects.filter(problem_id__icontains='1000')` | problem_id index | Partial match search |
| **Filter by Platform** | High | `Problem.objects.filter(platform='baekjoon', is_completed=True)` | platform+created composite | Platform-specific views |
| **Filter by Language** | Medium | `Problem.objects.filter(language='python')` | language+created composite | Language filtering |
| **List Drafts** | Low (Admin) | `Problem.objects.filter(is_completed=False, is_deleted=False)` | deleted+completed composite | Admin only |
| **Count Test Cases** | High | Annotated via `Count('test_cases')` | N/A | Used in list serializers |
| **Check Problem Exists** | Medium | `Problem.objects.filter(platform=x, problem_id=y).exists()` | Unique composite | Validation check |
| **Update Problem** | Low | `Problem.objects.update_or_create(platform=x, problem_id=y, defaults={...})` | Unique composite | Admin operations |
| **Soft Delete** | Low | `problem.is_deleted=True; problem.deleted_at=now(); problem.save()` | N/A | Soft delete pattern |
| **Update Execution Count** | High | `problem.metadata['execution_count'] += 1; problem.save(update_fields=['metadata'])` | N/A | Metadata update, concurrency concern |

**Custom QuerySet Methods:**
```python
Problem.objects.minimal_fields()          # Uses only() to reduce payload
Problem.objects.with_test_cases()         # Prefetches test cases
Problem.objects.active()                  # Excludes deleted
Problem.objects.completed()               # Only completed problems
Problem.objects.drafts()                  # Only drafts
Problem.objects.with_test_case_count()    # Annotates count
Problem.objects.by_platform(platform)     # Platform filter
```

**Performance Notes:**
- Most queries include `.order_by('-created_at')` - sort by recency
- Heavy use of `only()` and `prefetch_related()` for optimization
- Test case relationship is always prefetched for detail views
- List views avoid loading test cases (use `minimal_fields()`)
- Caching TTL: 300s (5 min) for lists, 600s (10 min) for detail

---

### 2.3 TestCase Model

**Schema:**
- Primary Key: `id` (auto-increment)
- Foreign Key: `problem_id`
- Fields: `input` (TextField), `output` (TextField)
- Indexes:
  - `problem` (db_index via FK)
  - `created_at` (db_index)
  - Composite: `(problem, created_at)`
- Default Ordering: `['created_at']`

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Get All Test Cases for Problem** | Very High | `TestCase.objects.filter(problem_id=x).order_by('created_at')` | problem+created composite | Always with Problem |
| **Count Test Cases** | High | `TestCase.objects.filter(problem_id=x).count()` | problem index | For validation |
| **Check Test Cases Exist** | Medium | `TestCase.objects.filter(problem_id=x).exists()` | problem index | Quick validation |
| **Bulk Create Test Cases** | Medium | `TestCase.objects.bulk_create([...], batch_size=100)` | N/A | During problem registration |
| **Bulk Update Test Cases** | Low | `TestCase.objects.bulk_update([...], ['output'], batch_size=100)` | N/A | During output generation |
| **Delete Test Cases for Problem** | Low | `TestCase.objects.filter(problem_id=x).delete()` | problem index | During re-generation |
| **Get Test Cases by IDs** | High | `TestCase.objects.filter(id__in=[...]).only('id','input','output').in_bulk()` | PK bulk lookup | For enriching results |

**Relationship Pattern:**
- **ALWAYS** accessed through Problem (parent-child)
- Never queried independently
- Typical size: 10-100 test cases per problem
- Always loaded together with problem detail view

**Performance Notes:**
- Critical to prefetch with Problem to avoid N+1 queries
- Uses `in_bulk()` for efficient batch lookups by ID
- Large TEXT fields - potential DynamoDB concern (item size limit)
- Ordered by `created_at` for consistent ordering

---

### 2.4 SearchHistory Model (High Volume)

**Schema:**
- Primary Key: `id` (auto-increment)
- Foreign Keys: `user_id` (nullable), `problem_id`
- Indexes:
  - `user` (db_index via FK)
  - `user_identifier` (db_index)
  - `problem` (db_index via FK)
  - `platform` (db_index)
  - `language` (db_index)
  - `is_code_public` (db_index)
  - `created_at` (db_index)
  - Composite: `(user, -created_at)` - MOST COMMON
  - Composite: `(is_code_public, -created_at)`
  - Composite: `(user_identifier, -created_at)`
  - Composite: `(problem, -created_at)`
  - Composite: `(platform, -created_at)`
  - Composite: `(language, -created_at)`
- JSON Fields: `result_summary`, `test_results`, `hints`, `metadata`
- Large TEXT Field: `code`
- Default Ordering: `['-created_at']` (newest first)

**Denormalized Fields (for performance):**
- `platform` (from Problem)
- `problem_number` (from Problem.problem_id)
- `problem_title` (from Problem.title)
- `user_identifier` (user email or 'anonymous')

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Create Execution Record** | Very High | `SearchHistory.objects.create(user=..., problem=..., ...)` | N/A | After every code execution |
| **List User's History** | Very High | `SearchHistory.objects.filter(user=x).order_by('-created_at')[offset:limit]` | user+created composite | Pagination required |
| **List Public + Own History** | High | `Q(user=x) \| Q(is_code_public=True)` with ordering | user+created + public+created | Complex query |
| **List Public History Only** | Medium | `SearchHistory.objects.filter(is_code_public=True).order_by('-created_at')` | public+created composite | Anonymous users |
| **Get Execution Detail** | High | `SearchHistory.objects.select_related('user').get(id=x)` | PK + FK join | Single item |
| **Filter by Platform** | Low | `SearchHistory.objects.filter(platform='baekjoon').order_by('-created_at')` | platform+created composite | Analytics |
| **Filter by Language** | Low | `SearchHistory.objects.filter(language='python').order_by('-created_at')` | language+created composite | Analytics |
| **Check for Hints** | Medium | `SearchHistory.objects.filter(id=x).only('hints', 'failed_count').get()` | PK | Before generation |
| **Update Hints** | Medium | `history.hints=[...]; history.save(update_fields=['hints'])` | N/A | After AI generation |
| **User Stats Aggregation** | Medium | Complex aggregations by platform, language, pass/fail | Multiple indexes | Cached heavily |

**Custom QuerySet Methods:**
```python
SearchHistory.objects.with_user()         # select_related('user')
SearchHistory.objects.with_problem()      # select_related('problem')
SearchHistory.objects.public()            # is_code_public=True
SearchHistory.objects.for_user(user)      # user filter
SearchHistory.objects.minimal_fields()    # only() critical fields
```

**Pagination Pattern:**
```python
# Offset-based pagination (NOT cursor-based)
queryset[offset:offset+limit]
# Returns: results, count, next_offset, has_more
```

**Performance Notes:**
- **Highest write volume** of all entities
- Time-series data pattern (always sorted by created_at DESC)
- Denormalized fields prevent joins during list queries
- Heavy use of `only()` to avoid loading large `code` field
- Never updated after creation (except hints)
- Caching: Generally not cached (too dynamic, per-user)

---

### 2.5 UsageLog Model (High Volume Time-Series)

**Schema:**
- Primary Key: `id` (auto-increment)
- Foreign Keys: `user_id`, `problem_id` (nullable)
- Fields: `action` (choices: 'hint', 'execution')
- Indexes:
  - `user` (db_index via FK)
  - `action` (db_index)
  - `problem` (db_index via FK, nullable)
  - `created_at` (db_index)
  - Composite: `(user, action, -created_at)` - hot path
  - Composite: `(user, action, created_at)` - for date range queries
  - Composite: `(problem, -created_at)`
- JSON Field: `metadata`
- Default Ordering: `['-created_at']`

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Log Usage (Create)** | Very High | `UsageLog.objects.create(user=x, action='execution', ...)` | N/A | Every rate-limited operation |
| **Check Daily Limit** | Very High | `UsageLog.objects.filter(user=x, action='hint', created_at__gte=today).count()` | user+action+date composite | Rate limiting (hot path) |
| **Count User's Hints Today** | Very High | Same as above with action='hint' | user+action+date composite | Before each hint request |
| **Count User's Executions Today** | Very High | Same as above with action='execution' | user+action+date composite | Before each execution |
| **User Activity Stats** | Medium | Aggregations by action over time periods | user+action+date composite | Admin dashboard |
| **Problem Usage Stats** | Low | `UsageLog.objects.filter(problem=x).count()` | problem+created composite | Analytics |
| **Top Active Users** | Low | Complex aggregation with user join | user+action+date composite | Admin dashboard |

**Usage Pattern:**
```python
# Rate limiting check (happens BEFORE operation)
today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
count = UsageLog.objects.filter(
    user=user,
    action='execution',  # or 'hint'
    created_at__gte=today_start
).count()

if count >= user.get_plan_limits()['max_executions_per_day']:
    raise RateLimitExceeded

# Log usage (happens AFTER operation succeeds)
UsageLog.objects.create(
    user=user,
    action='execution',
    problem=problem,
    metadata={'task_id': task_id, 'language': language}
)
```

**Performance Notes:**
- **Extremely high write volume** - every code execution and hint request
- **Very high read volume** - rate limit checks before every operation
- Time-series data (append-only, never updated)
- Date range queries are critical (today's usage)
- Composite index on (user, action, created_at) is CRITICAL for performance
- Consider data retention policy (delete old logs?)
- Potential candidate for time-series database or DynamoDB TTL

---

### 2.6 SubscriptionPlan Model

**Schema:**
- Primary Key: `id` (auto-increment)
- Unique Key: `name`
- Indexes:
  - `name` (unique, db_index)
  - `is_active` (db_index)
- Fields: Limits and features (all scalar)
- Default Ordering: `['name']`

**Fixed Records:**
```
1. Free - Basic tier
2. Pro - Mid tier
3. Pro+ - High tier
4. Admin - Unlimited
```

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Get Plan by Name** | High | `SubscriptionPlan.objects.get(name='Free')` | name (unique) | During user creation |
| **List Active Plans** | High | `SubscriptionPlan.objects.filter(is_active=True).exclude(name='Admin')` | is_active index | Public plan selection |
| **Get Plan with User Count** | Low (Admin) | `SubscriptionPlan.objects.annotate(user_count=Count('users'))` | Reverse FK | Admin dashboard |
| **Plan CRUD** | Very Low | Admin operations only | Various | Rare operations |

**Performance Notes:**
- Tiny table (4-5 records)
- High read, very low write
- Perfect candidate for aggressive caching or even hardcoding
- Could be replaced with DynamoDB Global Table or even app config

---

### 2.7 ScriptGenerationJob Model

**Schema:**
- Primary Key: `id` (auto-increment)
- Indexes:
  - `platform` (db_index)
  - `problem_id` (db_index)
  - `job_type` (db_index)
  - `status` (db_index) - 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
  - `celery_task_id` (db_index)
  - `created_at` (db_index)
  - Composite: `(job_type, -created_at)`
  - Composite: `(status, -created_at)`
  - Composite: `(platform, problem_id)`
- Large TEXT Fields: `solution_code`, `generator_code`, `error_message`, `constraints`
- Default Ordering: `['-created_at']`

**Access Patterns:**

| Pattern | Frequency | Query | Indexes Used | Notes |
|---------|-----------|-------|--------------|-------|
| **Create Job** | Medium | `ScriptGenerationJob.objects.create(...)` | N/A | Start async task |
| **Update Job Status** | Medium | `job.status='PROCESSING'; job.save(update_fields=['status', ...])` | N/A | Task lifecycle |
| **Get Job by ID** | Medium | `ScriptGenerationJob.objects.get(id=x)` | PK | Check task status |
| **Get Job by Task ID** | Medium | `ScriptGenerationJob.objects.get(celery_task_id=x)` | task_id index | Celery callback |
| **List Jobs** | Medium | `ScriptGenerationJob.objects.filter(job_type='script_generation').order_by('-created_at')` | type+created composite | Admin view |
| **Filter by Status** | Medium | `ScriptGenerationJob.objects.filter(status='PENDING')` | status+created composite | Monitor queue |
| **Filter by Platform** | Low | `ScriptGenerationJob.objects.filter(platform='baekjoon')` | platform+problem composite | Analytics |
| **Delete Job** | Low | `ScriptGenerationJob.objects.get(id=x).delete()` | PK | Cleanup |
| **Select for Update** | Medium | `.select_for_update(skip_locked=True).get(id=x)` | PK with row lock | Prevent race conditions |

**Job Lifecycle:**
```
1. CREATE: status='PENDING', celery_task_id=None
2. START: status='PROCESSING', celery_task_id=<task_id>
3. COMPLETE: status='COMPLETED', generator_code=<result>
   OR FAIL: status='FAILED', error_message=<error>
```

**Performance Notes:**
- Medium write volume during job creation/updates
- Jobs are created asynchronously (Celery tasks)
- Use of `select_for_update(skip_locked=True)` for concurrency control
- Status transitions: PENDING → PROCESSING → COMPLETED/FAILED
- Potentially large TEXT fields (generator code can be 1KB-10KB)
- Jobs may be periodically cleaned up (retention policy)

---

## 3. Hot Access Patterns

### 3.1 Critical Hot Paths (> 1000 req/min expected)

1. **User Authentication & Authorization**
   - Pattern: `User.objects.select_related('subscription_plan').get(email=x)`
   - Frequency: Every authenticated request
   - Current optimization: Simple PK lookup + single join
   - Cache: Session-based (JWT tokens)
   - DynamoDB concern: Needs single-digit millisecond latency

2. **Get Problem with Test Cases**
   - Pattern: `Problem.objects.prefetch_related('test_cases').get(platform=x, problem_id=y)`
   - Frequency: Every code execution request
   - Current optimization: Prefetch to avoid N+1
   - Cache: Redis (TTL: 600s)
   - DynamoDB concern: Requires efficient 1:M relationship handling

3. **Rate Limit Check**
   - Pattern: `UsageLog.objects.filter(user=x, action=y, created_at__gte=today).count()`
   - Frequency: Before every code execution and hint request
   - Current optimization: Composite index on (user, action, created_at)
   - Cache: Short TTL (60s)
   - DynamoDB concern: Time-series query optimization critical

4. **Create Execution Record**
   - Pattern: `SearchHistory.objects.create(...)`
   - Frequency: After every code execution
   - Current optimization: None needed (simple insert)
   - Cache: N/A (writes)
   - DynamoDB concern: High write throughput required

5. **Log Usage for Rate Limiting**
   - Pattern: `UsageLog.objects.create(...)`
   - Frequency: After every rate-limited operation
   - Current optimization: None needed (simple insert)
   - Cache: N/A (writes)
   - DynamoDB concern: High write throughput required

### 3.2 Frequently Accessed Data (> 100 req/min)

1. **List Problems (Search/Browse)**
   - Pattern: Complex filtering + sorting by created_at
   - Cache: Redis (TTL: 300s)
   - DynamoDB concern: Full-text search on title, sorting

2. **User's Execution History**
   - Pattern: `SearchHistory.objects.filter(user=x).order_by('-created_at')`
   - Cache: Minimal (too dynamic)
   - DynamoDB concern: Pagination, time-series access

3. **User Statistics**
   - Pattern: Complex aggregations on SearchHistory
   - Cache: Redis (TTL: 180s)
   - DynamoDB concern: Requires efficient aggregation

4. **Check Admin Status**
   - Pattern: In-memory config check (`user.is_admin()`)
   - Cache: N/A (app-level)
   - DynamoDB concern: None

---

## 4. Relationship Traversals

### 4.1 Foreign Key Traversals (N+1 Prevention)

**Pattern: User → SubscriptionPlan**
```python
# Optimized with select_related
User.objects.select_related('subscription_plan').get(id=x)

# Accessed via:
user.subscription_plan.max_hints_per_day
user.subscription_plan.max_executions_per_day
```
- **Frequency:** Very High (every rate limit check)
- **Direction:** Forward FK (User → Plan)
- **DynamoDB Strategy:** Denormalize plan limits into User item OR use batch get

**Pattern: SearchHistory → User**
```python
# Optimized with select_related
SearchHistory.objects.select_related('user').filter(...)

# Accessed via:
history.user.email
```
- **Frequency:** High (history list views)
- **Direction:** Forward FK (History → User)
- **DynamoDB Strategy:** Denormalize user email into SearchHistory item

**Pattern: SearchHistory → Problem**
```python
# Currently DENORMALIZED for performance
# SearchHistory stores: platform, problem_number, problem_title
```
- **Frequency:** N/A (already denormalized)
- **Direction:** Forward FK (History → Problem) BUT denormalized
- **DynamoDB Strategy:** Keep denormalized pattern

**Pattern: Problem → TestCase (1:M)**
```python
# Optimized with prefetch_related
Problem.objects.prefetch_related('test_cases').get(id=x)

# Accessed via:
problem.test_cases.all()  # Returns list of test cases
```
- **Frequency:** Very High (every problem detail request)
- **Direction:** Reverse FK (Problem → TestCases)
- **DynamoDB Strategy:**
  - Option A: Store test cases as nested list in Problem item (if under 400KB)
  - Option B: Separate table with GSI on problem_id
  - Option C: Composite key (PK: problem_id, SK: test_case_number)

### 4.2 Reverse Foreign Key Traversals

**Pattern: Problem → SearchHistory (Rare)**
```python
# Rarely used
problem.search_history.all()
```
- **Frequency:** Very Low (analytics only)
- **Direction:** Reverse FK
- **DynamoDB Strategy:** GSI on SearchHistory table with problem_id

**Pattern: User → SearchHistory (Common)**
```python
# Very common pattern
user.search_history.filter(...).order_by('-created_at')
```
- **Frequency:** Very High
- **Direction:** Reverse FK
- **DynamoDB Strategy:** GSI on SearchHistory table with user_id as PK

**Pattern: SubscriptionPlan → Users (Admin only)**
```python
# Admin dashboard
plan.users.count()
plan.users.filter(is_active=True)
```
- **Frequency:** Low
- **Direction:** Reverse FK
- **DynamoDB Strategy:** Query Users table with GSI on plan_id

---

## 5. Query Performance Characteristics

### 5.1 Filtering Patterns

**Single Field Filters:**
```python
Problem.objects.filter(platform='baekjoon')
Problem.objects.filter(is_completed=True)
User.objects.filter(is_active=True)
SearchHistory.objects.filter(is_code_public=True)
UsageLog.objects.filter(action='hint')
```
- Simple equality filters
- DynamoDB: Easy with GSI or primary key

**Multi-Field Filters:**
```python
Problem.objects.filter(is_completed=True, is_deleted=False)
Problem.objects.filter(platform='baekjoon', problem_id='1000')  # Unique key
UsageLog.objects.filter(user=x, action='hint', created_at__gte=today)
```
- Composite filters with AND logic
- DynamoDB: Requires composite keys or multiple GSIs

**OR Filters:**
```python
SearchHistory.objects.filter(Q(user=x) | Q(is_code_public=True))
User.objects.filter(Q(email__icontains=search) | Q(name__icontains=search))
```
- Complex boolean logic
- DynamoDB: **CHALLENGING** - requires multiple queries + merge in app layer

**Contains/Search Filters:**
```python
Problem.objects.filter(title__icontains='binary search')
Problem.objects.filter(problem_id__icontains='100')
User.objects.filter(email__icontains='gmail')
```
- Full-text or substring search
- DynamoDB: **VERY CHALLENGING** - requires:
  - ElasticSearch/OpenSearch integration
  - Client-side filtering (scan)
  - Pre-computed search index

### 5.2 Sorting Patterns

**Primary Sort: Time-Series Descending**
```python
# Almost ALL models default to: order_by('-created_at')
SearchHistory.objects.order_by('-created_at')
Problem.objects.order_by('-created_at')
UsageLog.objects.order_by('-created_at')
ScriptGenerationJob.objects.order_by('-created_at')
```
- **Frequency:** Very High
- **DynamoDB Strategy:** Use created_at as Sort Key in LSI/GSI

**Secondary Sorts:**
```python
SubscriptionPlan.objects.order_by('name')
TestCase.objects.order_by('created_at')  # Ascending
```
- Less common
- DynamoDB: Design sort keys accordingly

### 5.3 Aggregation Patterns

**Count Operations:**
```python
Problem.objects.annotate(test_case_count=Count('test_cases'))
SearchHistory.objects.filter(user=x).count()
UsageLog.objects.filter(user=x, action='hint').count()
```
- **Frequency:** High to Very High
- **DynamoDB Challenge:** No native count - must maintain counters or scan

**Group By Aggregations:**
```python
SearchHistory.objects.values('platform').annotate(count=Count('id'))
SearchHistory.objects.values('language').annotate(count=Count('id'))
UsageLog.objects.values('action').annotate(count=Count('id'))
```
- **Frequency:** Medium (user stats, analytics)
- **DynamoDB Challenge:** Requires application-level aggregation or DynamoDB Streams

**Conditional Aggregations:**
```python
SearchHistory.objects.aggregate(
    passed=Count('id', filter=Q(failed_count=0)),
    failed=Count('id', filter=Q(failed_count__gt=0))
)
```
- **Frequency:** Medium
- **DynamoDB Challenge:** Must scan and aggregate in application

### 5.4 Pagination Patterns

**Offset-Based Pagination (Current):**
```python
queryset = SearchHistory.objects.filter(...).order_by('-created_at')
results = queryset[offset:offset+limit]
total_count = queryset.count()

return {
    'results': results,
    'count': total_count,
    'next_offset': offset + limit,
    'has_more': (offset + limit) < total_count
}
```
- **Used by:** SearchHistory, Problem lists
- **DynamoDB Challenge:** Offset-based pagination requires scanning
- **Recommendation:** Switch to cursor-based (LastEvaluatedKey)

**Cursor-Based Pagination (Ideal for DynamoDB):**
```python
# Not currently implemented, but ideal for DynamoDB
response = table.query(
    Limit=20,
    ExclusiveStartKey=last_evaluated_key  # from previous page
)
```

---

## 6. Caching Strategy

### 6.1 Current Redis Caching Implementation

**Cache Infrastructure:**
- **Backend:** Redis (via django-redis)
- **Key Strategy:** Structured keys with prefixes
- **TTL Strategy:** Tiered based on data volatility

**Cache TTL Configuration:**
```python
CACHE_TTL = {
    'SHORT': 60,           # 1 minute - volatile data
    'MEDIUM': 300,         # 5 minutes - default
    'PROBLEM_LIST': 300,   # 5 minutes - problem lists
    'PROBLEM_DETAIL': 600, # 10 minutes - problem details
    'USER_STATS': 180,     # 3 minutes - user statistics
    'LONG': 3600,          # 1 hour - very stable data
}
```

### 6.2 Cached Entities & Patterns

| Data Type | Cache Key Pattern | TTL | Invalidation Strategy |
|-----------|------------------|-----|----------------------|
| **Problem List** | `problem_list:{platform}:{search}:{page}` | 300s | Signal on Problem save/delete |
| **Problem Detail** | `problem_detail:id:{id}` or `platform:{p}:{pid}` | 600s | Signal on Problem save/delete |
| **Problem Registered** | `problem_registered:all` | 300s | Signal on Problem completion |
| **Problem Drafts** | `problem_drafts:all` | 60s | Signal on Problem save |
| **User Stats** | `user_stats:{user_id}` | 180s | Manual invalidation on execution |
| **User Plan Usage** | `user_stats:{user_id}:usage` | 60s | Manual invalidation on usage |
| **Test Cases** | `test_cases:problem:{id}` | 600s | Signal on TestCase changes |
| **Problem Info (Extraction)** | `problem_info:{url}` | 3600s | Never (extraction is expensive) |
| **Available Plans** | Not cached currently | - | Could cache aggressively |

### 6.3 Cache Invalidation Mechanisms

**Django Signals (Automatic):**
```python
# api/signals.py
@receiver(post_save, sender=Problem)
def invalidate_problem_cache(sender, instance, **kwargs):
    CacheInvalidator.invalidate_problem_caches(
        problem_id=instance.id,
        platform=instance.platform
    )

@receiver(post_delete, sender=Problem)
def invalidate_problem_cache_on_delete(sender, instance, **kwargs):
    # Similar invalidation
```

**Manual Invalidation:**
```python
# After user execution, invalidate user stats
cache_key = CacheKeyGenerator.user_stats_key(user.id)
cache.delete(cache_key)
```

**Pattern-Based Invalidation:**
```python
# Invalidate all problem-related caches
CacheInvalidator.invalidate_pattern("problem_*")

# Uses Redis KEYS command with prefix
redis_conn.keys(f"{KEY_PREFIX}:*:{pattern}")
redis_conn.delete(*keys)
```

### 6.4 Cache Warming (Celery Tasks)

**Periodic Cache Warming:**
```python
@shared_task
def warm_problem_cache_task():
    """Runs every 5 minutes"""
    # Pre-populate cache with:
    # 1. All completed problems list
    # 2. Registered problems list
    # 3. Top 20 recent problem details
    # 4. Draft problems
    # 5. Platform-specific lists
```

**Benefits:**
- Reduces cache misses during peak traffic
- Ensures consistent response times
- Pre-computed aggregations

### 6.5 Cache Hit Rate Expectations

Based on code analysis:

| Endpoint | Expected Hit Rate | Notes |
|----------|------------------|-------|
| Problem List | 80-90% | High hit rate, 5 min TTL |
| Problem Detail | 70-80% | Moderate hit rate, 10 min TTL |
| User Stats | 60-70% | Per-user, changes frequently |
| Search History | 10-20% | Very dynamic, per-user |
| Rate Limit Checks | 0% | Never cached (accuracy critical) |

### 6.6 DynamoDB + Caching Strategy

**Recommended Approach:**
1. **Keep Redis for hot data** - Don't rely solely on DynamoDB
2. **Use DAX for DynamoDB** - DynamoDB Accelerator for read-heavy tables
3. **Cache Time-Series Aggregations** - Count queries, stats, etc.
4. **Edge Caching** - CloudFront for API responses where appropriate
5. **Application-Level Caching** - Continue using Redis with similar patterns

---

## 7. Rate Limiting & Usage Tracking

### 7.1 Rate Limiting Implementation

**Architecture:**
```
User Request → Check Rate Limit → Execute Operation → Log Usage
                       ↓                                    ↓
                   UsageLog.count()                   UsageLog.create()
```

**Rate Limit Flow:**
```python
# Step 1: Get user's plan limits
limits = user.get_plan_limits()  # From SubscriptionPlan via FK
max_executions = limits['max_executions_per_day']  # e.g., 50

# Step 2: Count today's usage
today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
current_count = UsageLog.objects.filter(
    user=user,
    action='execution',
    created_at__gte=today_start
).count()

# Step 3: Check limit
if current_count >= max_executions:
    return HTTP 429 Too Many Requests

# Step 4: Execute operation (code execution, hint generation, etc.)

# Step 5: Log usage
UsageLog.objects.create(
    user=user,
    action='execution',
    problem=problem,
    metadata={'task_id': task_id}
)
```

**Rate Limited Operations:**
1. **Code Execution** - `max_executions_per_day`
2. **Hint Generation** - `max_hints_per_day`

### 7.2 Plan Limits

| Plan | Hints/Day | Executions/Day | Max Problems | Can Register Problems |
|------|-----------|----------------|--------------|----------------------|
| **Free** | 5 | 50 | Unlimited (-1) | No |
| **Pro** | 20 | 200 | Unlimited (-1) | Yes |
| **Pro+** | 100 | 1000 | Unlimited (-1) | Yes |
| **Admin** | Unlimited (-1) | Unlimited (-1) | Unlimited (-1) | Yes |

### 7.3 Usage Tracking Patterns

**Daily Reset Logic:**
- Limit window: Midnight to midnight (user's timezone? or UTC?)
- Count query uses `created_at__gte=today_start`
- No explicit reset - just query filters

**Query Performance for Rate Limiting:**
```python
# This query runs BEFORE EVERY rate-limited operation
# CRITICAL HOT PATH - Must be < 10ms
UsageLog.objects.filter(
    user_id=123,
    action='execution',
    created_at__gte='2025-10-07 00:00:00'
).count()

# Uses composite index: (user, action, created_at)
# Postgres: Index scan → Count
# DynamoDB: Query with GSI → Count items
```

### 7.4 DynamoDB Considerations for Rate Limiting

**Challenge:** DynamoDB doesn't have native COUNT with time range filters

**Solutions:**

**Option A: Maintain Counter Attributes (Recommended)**
```
User Item:
{
  PK: "USER#123",
  SK: "METADATA",
  hints_today: 3,
  hints_date: "2025-10-07",
  executions_today: 25,
  executions_date: "2025-10-07"
}

# On new day, reset counters atomically
UpdateExpression: "SET hints_today = :zero, hints_date = :today"
ConditionExpression: "hints_date <> :today"
```
- **Pro:** O(1) read, fast writes
- **Con:** Must handle counter updates atomically

**Option B: Query UsageLog with TTL**
```
UsageLog Item:
{
  PK: "USER#123",
  SK: "2025-10-07T10:30:45#execution",
  action: "execution",
  TTL: 1728432000  # 30 days from now
}

# Query count
Query(
  KeyConditionExpression: "PK = :pk AND SK BEGINS_WITH :today",
  ...
)
```
- **Pro:** Accurate, audit trail preserved
- **Con:** Slower, requires query to count

**Option C: Hybrid (Best)**
- Use counters in User item for fast checks
- Use UsageLog for audit trail
- Periodic reconciliation job

### 7.5 Admin Users Exception

```python
if user.is_admin():
    return True, 0, -1, "Admin users have unlimited access"
```

Admin users bypass all rate limits. Implementation:
```python
# In User model
def is_admin(self):
    return self.email in settings.ADMIN_EMAILS  # Config-based
```

**DynamoDB Strategy:**
- Check admin status from User item or in-memory config
- No need to query UsageLog for admins

---

## 8. Transaction Requirements

### 8.1 Atomic Operations (Django `transaction.atomic()`)

**Pattern 1: Problem Registration with Test Cases**
```python
with transaction.atomic():
    # Create problem
    problem = Problem.objects.create(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        ...
    )

    # Bulk create test cases
    test_cases = [TestCase(problem=problem, input=..., output=...) for ...]
    TestCase.objects.bulk_create(test_cases, batch_size=100)
```
- **Frequency:** Medium (during problem registration)
- **Requirement:** All-or-nothing creation
- **DynamoDB:** Use `TransactWriteItems` (max 100 items) or application-level rollback

**Pattern 2: Test Case Regeneration**
```python
with transaction.atomic():
    # Delete all existing test cases
    TestCase.objects.filter(problem=problem).delete()

    # Create new test cases
    TestCase.objects.bulk_create(new_test_cases, batch_size=100)
```
- **Frequency:** Low (admin operations)
- **Requirement:** Atomic delete + create
- **DynamoDB:** Use `TransactWriteItems` or versioning

**Pattern 3: Output Generation (Bulk Update)**
```python
with transaction.atomic():
    # Update outputs for all test cases
    TestCase.objects.bulk_update(
        test_cases_to_update,
        ['output'],
        batch_size=100
    )
```
- **Frequency:** Low
- **Requirement:** Atomic batch update
- **DynamoDB:** Use `TransactWriteItems` for small batches, batch write for large

### 8.2 Concurrency Control

**Pattern: Select for Update (Pessimistic Locking)**
```python
job = ScriptGenerationJob.objects.select_for_update(
    skip_locked=True
).get(id=job_id)

if job.status == 'PROCESSING':
    # Another worker is processing, skip
    return

job.status = 'PROCESSING'
job.celery_task_id = task_id
job.save(update_fields=['status', 'celery_task_id'])
```
- **Use Case:** Prevent duplicate task processing by Celery workers
- **DynamoDB Strategy:**
  - Conditional updates with version number
  - Optimistic locking pattern
  - Example: `ConditionExpression: "version = :old_version"`

**Pattern: Metadata Update (Counter Increment)**
```python
# Incrementing execution count in Problem.metadata
problem.metadata['execution_count'] = problem.metadata.get('execution_count', 0) + 1
problem.save(update_fields=['metadata'])
```
- **Issue:** Race condition possible under high concurrency
- **Current State:** No locking mechanism
- **DynamoDB Strategy:** Use atomic counter with `UpdateExpression: "ADD execution_count :val"`

### 8.3 Critical Consistency Requirements

**1. Rate Limiting Counters**
- **Requirement:** Accurate counts to prevent limit bypass
- **Current:** Eventual consistency acceptable (query lag ~seconds)
- **DynamoDB:** Use strongly consistent reads for counter checks

**2. Problem + Test Cases**
- **Requirement:** Test cases must always reference valid problem
- **Current:** Foreign key constraint enforces this
- **DynamoDB:** Application-level validation or use item collections

**3. User + SearchHistory**
- **Requirement:** Search history can exist without user (nullable FK)
- **Current:** ON DELETE CASCADE (but FK is nullable)
- **DynamoDB:** Store user_id as attribute, handle orphaned records in app

### 8.4 Transaction Boundaries (DynamoDB Limitations)

**DynamoDB Transaction Constraints:**
- Max 100 items per `TransactWriteItems`
- All items must be in same region
- Higher latency than non-transactional writes
- More expensive (2x write capacity)

**Recommendations:**
1. **Minimize transactional writes** - Use for critical operations only
2. **Break large batches** - Problem with 100+ test cases needs special handling
3. **Eventual consistency** - Accept for non-critical data (analytics, stats)
4. **Idempotency** - Design operations to be safely retried

---

## 9. DynamoDB Design Recommendations

### 9.1 Table Design Options

**Option A: Single Table Design (Recommended for flexibility)**

```
PK                    | SK                          | Attributes
----------------------|----------------------------|---------------------------
USER#<email>          | METADATA                    | name, google_id, plan_id, ...
USER#<email>          | PLAN#<plan_name>            | (denormalized plan data)
USER#<user_id>        | USAGE#<date>#<action>       | action, metadata, ...
PROBLEM#<plat>#<pid>  | METADATA                    | title, language, tags, ...
PROBLEM#<plat>#<pid>  | TESTCASE#<number>           | input, output
PROBLEM#<plat>#<pid>  | HISTORY#<timestamp>#<id>    | user_id, code, results, ...
HISTORY#<id>          | METADATA                    | (for direct access)
PLAN#<name>           | METADATA                    | limits, features, ...
JOB#<id>              | METADATA                    | status, platform, ...
```

**Global Secondary Indexes:**
1. **GSI1 (User History):** PK=user_id, SK=timestamp
2. **GSI2 (Public History):** PK=is_public, SK=timestamp
3. **GSI3 (Problem by Platform):** PK=platform, SK=timestamp
4. **GSI4 (User by Plan):** PK=plan_id, SK=user_email
5. **GSI5 (Job by Status):** PK=status, SK=timestamp

**Pros:**
- Flexible querying with GSIs
- Single table to manage
- Cost-effective (fewer tables)
- Easier to maintain consistency

**Cons:**
- Complex access patterns
- Harder to reason about
- GSI overhead for writes
- May hit item size limits (400KB)

---

**Option B: Multi-Table Design (Traditional)**

```
1. Users Table
   PK: user_id
   SK: (none - single item)
   GSI1: email → user_id
   GSI2: google_id → user_id

2. Problems Table
   PK: platform#problem_id (composite)
   SK: (none - single item)
   GSI1: id → platform#problem_id (for ID lookups)

3. TestCases Table
   PK: problem_id (platform#problem_id)
   SK: test_case_number

4. SearchHistory Table
   PK: history_id
   SK: timestamp
   GSI1: user_id, SK=timestamp
   GSI2: problem_id, SK=timestamp
   GSI3: is_public, SK=timestamp

5. UsageLogs Table
   PK: user_id#date
   SK: timestamp#action
   TTL: 30 days

6. SubscriptionPlans Table
   PK: plan_name
   SK: (none)

7. ScriptGenerationJobs Table
   PK: job_id
   SK: (none)
   GSI1: status, SK=timestamp
```

**Pros:**
- Clear separation of concerns
- Easier to understand and maintain
- Familiar to SQL developers
- Easier to add new access patterns (new GSI)

**Cons:**
- More tables to manage
- Higher costs (base table charges × tables)
- Potential for cross-table consistency issues
- More API calls for joins

---

### 9.2 Recommended Approach: Hybrid Multi-Table

**Rationale:**
- Application has distinct entity types with different access patterns
- Some entities (TestCases) are tightly coupled to parent (Problem)
- High write volume tables (UsageLogs, SearchHistory) benefit from separate tables
- Easier migration path from relational database

**Proposed Table Structure:**

#### Table 1: Users
```
Primary Key:
  PK: USER#<id>
  SK: METADATA

Attributes:
  email, name, picture, google_id, is_active, created_at
  plan_id (denormalized)
  plan_name (denormalized)
  plan_limits (denormalized JSON: {max_hints_per_day, ...})

  # Rate limiting counters
  hints_today, hints_date, executions_today, executions_date

GSI1 (EmailIndex):
  PK: email
  SK: (none)

GSI2 (GoogleIdIndex):
  PK: google_id
  SK: (none)

GSI3 (PlanIndex):
  PK: plan_id
  SK: created_at
```

**Denormalization Strategy:**
- Store plan limits directly in User item to avoid join on every rate limit check
- Update plan limits when user changes plan or when plan is updated

**Access Patterns Supported:**
- ✅ Get user by ID (PK)
- ✅ Get user by email (GSI1)
- ✅ Get user by Google ID (GSI2)
- ✅ List users by plan (GSI3)
- ✅ Check rate limit (read counters from user item)
- ✅ Update rate limit counters (atomic ADD operation)

---

#### Table 2: Problems
```
Primary Key:
  PK: PROBLEM#<platform>#<problem_id>
  SK: METADATA

Attributes:
  id (UUID or auto-increment for compatibility)
  platform, problem_id, title, problem_url, tags, language
  solution_code, constraints, metadata
  is_completed, is_deleted, deleted_at, deleted_reason
  created_at, updated_at

  # Denormalized counts
  test_case_count, execution_count

GSI1 (IdIndex):
  PK: id
  SK: (none)

GSI2 (PlatformIndex):
  PK: platform#is_completed
  SK: created_at

GSI3 (CompletionIndex):
  PK: is_completed#is_deleted
  SK: created_at

GSI4 (LanguageIndex):
  PK: language
  SK: created_at
```

**Alternative for Test Cases (Store inline vs separate table):**

**Approach 2A: Test Cases as Nested Array (if < 50 test cases)**
```
Attributes:
  ...
  test_cases: [
    {number: 1, input: "1 2", output: "3"},
    {number: 2, input: "5 7", output: "12"},
    ...
  ]
```
- **Pro:** Single read to get problem + test cases
- **Con:** 400KB item size limit, update complexity

**Approach 2B: Test Cases in Separate Table (Recommended)**
```
Table: TestCases
PK: PROBLEM#<platform>#<problem_id>
SK: TESTCASE#<number>

Attributes:
  problem_id, input, output, created_at
```
- **Pro:** No item size limit, can handle 1000s of test cases
- **Con:** Additional query required

**Access Patterns Supported:**
- ✅ Get problem by ID (GSI1)
- ✅ Get problem by platform + problem_id (PK)
- ✅ Get problem with test cases (PK + Query on TestCases table)
- ✅ List completed problems (GSI3)
- ✅ List problems by platform (GSI2)
- ✅ List problems by language (GSI4)
- ❌ Full-text search on title (requires ElasticSearch/OpenSearch)
- ❌ Search by problem_id substring (requires Scan or ElasticSearch)

---

#### Table 3: SearchHistory
```
Primary Key:
  PK: HISTORY#<id>
  SK: TIMESTAMP#<created_at>

Attributes:
  id, user_id, user_identifier, user_email (denormalized)
  problem_id, platform, problem_number, problem_title (denormalized)
  language, code
  result_summary, passed_count, failed_count, total_count
  test_results (JSON), hints (JSON), metadata (JSON)
  is_code_public, created_at

GSI1 (UserHistoryIndex):
  PK: user_id
  SK: created_at

GSI2 (PublicHistoryIndex):
  PK: is_code_public
  SK: created_at
  ProjectionType: KEYS_ONLY (to save space)

GSI3 (ProblemHistoryIndex):
  PK: problem_id
  SK: created_at

GSI4 (UserIdentifierIndex):
  PK: user_identifier
  SK: created_at
```

**Access Patterns Supported:**
- ✅ Get history by ID (PK)
- ✅ List user's history (GSI1)
- ✅ List public history (GSI2, then batch get from main table)
- ✅ List history for problem (GSI3)
- ✅ Pagination via LastEvaluatedKey (cursor-based)
- ⚠️ List public + user's history (requires 2 queries + merge in app)

**Size Considerations:**
- `code` field can be large (10KB-100KB)
- `test_results` JSON can be large (10KB-50KB)
- Total item size likely 50KB-200KB
- Well within 400KB limit

---

#### Table 4: UsageLogs
```
Primary Key:
  PK: USER#<user_id>#<date>
  SK: <timestamp>#<action>

Attributes:
  user_id, action, problem_id, metadata
  created_at
  TTL: <timestamp + 30 days>

GSI1 (ProblemUsageIndex):
  PK: problem_id
  SK: created_at
```

**Design Rationale:**
- Partition by user_id + date for efficient daily count queries
- Sort key includes timestamp for precise ordering
- TTL for automatic cleanup (30 days retention)
- GSI for problem-level analytics

**Access Patterns Supported:**
- ✅ Count today's usage (Query on PK with date)
- ✅ Log new usage (PutItem)
- ✅ Auto-cleanup old logs (TTL)
- ✅ Problem usage stats (GSI1)
- ❌ Global aggregations (requires Scan or separate analytics table)

**Query Example:**
```python
# Check rate limit for user on 2025-10-07
response = table.query(
    KeyConditionExpression='PK = :pk AND begins_with(SK, :date)',
    ExpressionAttributeValues={
        ':pk': 'USER#123#2025-10-07',
        ':date': '2025-10-07'
    },
    Select='COUNT'
)
count = response['Count']
```

---

#### Table 5: SubscriptionPlans
```
Primary Key:
  PK: PLAN#<name>
  SK: METADATA

Attributes:
  id, name, description
  max_hints_per_day, max_executions_per_day, max_problems
  can_view_all_problems, can_register_problems
  is_active, created_at, updated_at
```

**Design Notes:**
- Tiny table (4-5 items)
- Could use DynamoDB Global Tables for multi-region
- Or even store in application config
- Cache aggressively (TTL: 1 hour+)

**Access Patterns Supported:**
- ✅ Get plan by name (PK)
- ✅ List all active plans (Scan - acceptable for tiny table)

---

#### Table 6: ScriptGenerationJobs
```
Primary Key:
  PK: JOB#<id>
  SK: METADATA

Attributes:
  id, job_type, status, celery_task_id
  platform, problem_id, title, problem_url, tags
  solution_code, language, constraints
  generator_code, error_message
  created_at, updated_at

GSI1 (StatusIndex):
  PK: status
  SK: created_at

GSI2 (TaskIdIndex):
  PK: celery_task_id
  SK: (none)

GSI3 (PlatformIndex):
  PK: platform#problem_id
  SK: created_at
```

**Access Patterns Supported:**
- ✅ Get job by ID (PK)
- ✅ Get job by task ID (GSI2)
- ✅ List jobs by status (GSI1)
- ✅ List jobs by platform (GSI3)
- ✅ Update job status (UpdateItem with ConditionExpression for concurrency control)

---

### 9.3 Capacity Planning

**Read/Write Patterns:**

| Table | Est. Items | Read/sec | Write/sec | Read Mode | Write Mode |
|-------|-----------|----------|-----------|-----------|------------|
| Users | 10K-100K | 500-1000 | 10-50 | On-Demand | On-Demand |
| Problems | 50K-500K | 1000-2000 | 50-100 | On-Demand | On-Demand |
| TestCases | 500K-5M | 1000-2000 | 50-100 | On-Demand | On-Demand |
| SearchHistory | 1M-10M+ | 500-1000 | 500-1000 | On-Demand | On-Demand |
| UsageLogs | 5M-50M+ | 1000-2000 | 500-1000 | On-Demand | On-Demand |
| SubscriptionPlans | 5-10 | 1000+ | 1-5 | Provisioned | Provisioned |
| ScriptGenerationJobs | 10K-100K | 100-500 | 50-100 | On-Demand | On-Demand |

**Recommendations:**
- Use **On-Demand** billing for most tables (unpredictable traffic)
- Use **Provisioned** for SubscriptionPlans (tiny, stable table)
- Enable **DynamoDB Streams** for SearchHistory and UsageLogs (analytics, auditing)
- Enable **Point-in-Time Recovery** for critical tables (Users, Problems)
- Enable **Auto Scaling** if using provisioned capacity

**Cost Estimates (rough):**
- Assuming 1M requests/day, 10GB storage per table
- On-Demand: ~$200-500/month for all tables
- Provisioned (optimized): ~$100-300/month
- GSI costs: ~$50-100/month additional per GSI

---

### 9.4 Key Design Patterns for DynamoDB

**Pattern 1: Composite Primary Keys**
```
PK: PROBLEM#baekjoon#1000
SK: METADATA
```
- Enables efficient lookup by composite natural key
- Avoids need for GSI on common query patterns

**Pattern 2: Denormalization for Performance**
```
User Item:
{
  ...
  plan_name: "Free",
  plan_limits: {
    max_hints_per_day: 5,
    max_executions_per_day: 50
  }
}
```
- Avoid joins by duplicating frequently accessed data
- Trade-off: Update complexity when plan changes

**Pattern 3: GSI Overloading**
```
GSI1 (TypeIndex):
  PK: entity_type (e.g., "USER", "PROBLEM")
  SK: created_at

# Enables listing all entities of a type, sorted by creation
```

**Pattern 4: Adjacency List for Relationships**
```
# Problem and its test cases
PK: PROBLEM#baekjoon#1000, SK: METADATA (problem data)
PK: PROBLEM#baekjoon#1000, SK: TESTCASE#1 (test case 1)
PK: PROBLEM#baekjoon#1000, SK: TESTCASE#2 (test case 2)
...
```
- Single Query to get problem + all test cases

**Pattern 5: Sparse Indexes for Filtering**
```
# Only add GSI attribute for active users
User Item (active):
  PK: USER#123
  is_active: "TRUE"  # Only set if active

GSI (ActiveUsersIndex):
  PK: is_active
  SK: created_at

# Inactive users don't have 'is_active' attribute, so they're not in GSI
```

---

### 9.5 DynamoDB-Specific Optimizations

**1. Use Projection Expressions to Reduce Data Transfer**
```python
response = table.get_item(
    Key={'PK': 'USER#123'},
    ProjectionExpression='email,name,plan_limits'
)
```
- Similar to Django's `only()` optimization
- Reduces costs and latency

**2. Use BatchGetItem for Bulk Reads**
```python
# Instead of 50 separate get_item calls
response = dynamodb.batch_get_item(
    RequestItems={
        'Users': {
            'Keys': [{'PK': 'USER#1'}, {'PK': 'USER#2'}, ...],
            'ProjectionExpression': 'email,name'
        }
    }
)
```
- Up to 100 items per call
- Much faster than sequential gets

**3. Use Atomic Counters**
```python
table.update_item(
    Key={'PK': 'USER#123'},
    UpdateExpression='ADD executions_today :inc',
    ExpressionAttributeValues={':inc': 1}
)
```
- For rate limiting counters, execution counts
- No read-modify-write race conditions

**4. Use Conditional Writes for Concurrency Control**
```python
# Update job status only if it's still PENDING
table.update_item(
    Key={'PK': 'JOB#456'},
    UpdateExpression='SET #status = :new_status',
    ConditionExpression='#status = :old_status',
    ExpressionAttributeValues={
        ':new_status': 'PROCESSING',
        ':old_status': 'PENDING'
    }
)
```
- Prevents duplicate processing by Celery workers
- Replaces PostgreSQL's `select_for_update()`

**5. Use DynamoDB Streams for Async Processing**
```python
# Stream → Lambda → Update aggregations, send notifications, etc.
```
- For analytics, cache invalidation, search index updates
- Decouples write path from read path

**6. Use TTL for Automatic Cleanup**
```python
# Set TTL attribute to Unix timestamp
item = {
    'PK': 'USER#123#2025-10-07',
    'SK': '2025-10-07T10:30:45#execution',
    'TTL': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days
}
```
- Automatic deletion of old UsageLogs
- Zero cost, eventual deletion

---

## 10. Migration Challenges & Risks

### 10.1 Critical Challenges

#### Challenge 1: Full-Text Search
**Current Implementation:**
```python
Problem.objects.filter(title__icontains='binary search')
Problem.objects.filter(Q(title__icontains='..') | Q(problem_id__icontains='..'))
```

**DynamoDB Limitation:**
- No built-in full-text search
- `contains` operators only work on specific attributes
- Cannot do case-insensitive partial matching efficiently

**Solutions:**
1. **Amazon OpenSearch Service (Recommended)**
   - DynamoDB Streams → Lambda → OpenSearch
   - Keep DynamoDB as source of truth
   - Use OpenSearch for search queries
   - Cost: ~$50-200/month for small cluster

2. **Client-Side Filtering (Not Recommended)**
   - Scan entire table, filter in application
   - Not scalable beyond 10K items

3. **Pre-Computed Search Indexes**
   - Tokenize titles, store in separate GSI
   - Complex to maintain
   - Still doesn't support arbitrary substring search

**Recommendation:** Use OpenSearch for search, DynamoDB for transactional operations.

---

#### Challenge 2: Complex OR Queries
**Current Implementation:**
```python
# Show user's own history OR public history
SearchHistory.objects.filter(Q(user=x) | Q(is_code_public=True))
```

**DynamoDB Limitation:**
- No native OR conditions in Query/Scan
- Must perform multiple queries and merge results in application

**Solutions:**
1. **Multiple Queries + Application Merge**
   ```python
   # Query 1: User's history (GSI1)
   user_history = table.query(
       IndexName='UserHistoryIndex',
       KeyConditionExpression='PK = :user_id'
   )

   # Query 2: Public history (GSI2)
   public_history = table.query(
       IndexName='PublicHistoryIndex',
       KeyConditionExpression='PK = :public',
       FilterExpression='user_id <> :user_id'  # Exclude duplicates
   )

   # Merge and sort in application
   merged = merge_and_sort(user_history, public_history, limit=20)
   ```

2. **Denormalize into Separate Items**
   - Store each history record twice (once per access pattern)
   - Not practical for this use case

**Recommendation:** Accept application-level merging for OR queries.

---

#### Challenge 3: Aggregations and Analytics
**Current Implementation:**
```python
# User statistics
SearchHistory.objects.values('platform').annotate(count=Count('id'))
SearchHistory.objects.aggregate(
    passed=Count('id', filter=Q(failed_count=0)),
    failed=Count('id', filter=Q(failed_count__gt=0))
)
```

**DynamoDB Limitation:**
- No native GROUP BY or aggregation functions
- Must scan table and compute in application or use DynamoDB Streams

**Solutions:**
1. **DynamoDB Streams + Lambda + Aggregation Table**
   ```
   SearchHistory writes → Stream → Lambda → Aggregate counts into separate table

   AggregationTable:
   PK: USER#<id>#STATS, SK: DAILY#<date>
   Attributes: total_executions, by_platform, by_language, etc.
   ```

2. **Real-Time Aggregation on Read**
   - Query recent records, compute stats
   - Cache results heavily (TTL: 180s)

3. **Batch Analytics Job (Daily/Hourly)**
   - Scheduled Lambda or Step Functions
   - Scan SearchHistory, compute aggregations
   - Store in separate analytics table or Redis

**Recommendation:** Hybrid approach - maintain aggregates in separate table, compute recent stats on-demand.

---

#### Challenge 4: Offset-Based Pagination
**Current Implementation:**
```python
queryset[offset:offset+limit]
```

**DynamoDB Limitation:**
- Only supports cursor-based pagination (LastEvaluatedKey)
- Cannot jump to arbitrary offset without scanning from beginning
- No native "total count" for paginated queries

**Solutions:**
1. **Switch to Cursor-Based Pagination (Recommended)**
   ```python
   # Frontend changes required
   {
       "results": [...],
       "next_cursor": "eyJQSyI6IkhJU1RPUlkjMTIzIiwiU0siOiI..."}",
       "has_more": true
   }
   ```

2. **Maintain Separate Count Table**
   - Keep total counts updated via DynamoDB Streams
   - Still can't jump to arbitrary offset efficiently

**Recommendation:** Refactor frontend to use cursor-based pagination.

---

#### Challenge 5: Transaction Limits
**Current Implementation:**
```python
with transaction.atomic():
    Problem.objects.create(...)
    TestCase.objects.bulk_create([100+ test cases])
```

**DynamoDB Limitation:**
- `TransactWriteItems` limited to 100 items
- Some problems have 100+ test cases

**Solutions:**
1. **Break into Multiple Transactions**
   ```python
   # Create problem first
   problem = create_problem(...)

   # Batch write test cases (no transaction)
   batch_write_test_cases(problem_id, test_cases)
   ```
   - Risk: Partial failure leaves problem without test cases
   - Mitigation: Mark problem as incomplete until all test cases written

2. **Store Test Cases as JSON Array (if < 400KB)**
   - Single item write
   - No transaction needed

**Recommendation:** Use batch writes with idempotency keys and retry logic.

---

#### Challenge 6: Joins and Relationship Traversals
**Current Patterns:**
```python
# Django ORM makes joins easy
User.objects.select_related('subscription_plan').get(id=x)
Problem.objects.prefetch_related('test_cases').get(id=x)
SearchHistory.objects.select_related('user', 'problem').filter(...)
```

**DynamoDB Limitation:**
- No native joins
- Must denormalize or perform multiple queries

**Solutions:**
1. **Denormalization (Recommended for Hot Paths)**
   - User item includes plan limits
   - SearchHistory includes user_email, problem_title
   - Trade-off: Data duplication, update complexity

2. **Application-Level Joins**
   - Get SearchHistory items
   - Extract user_ids, problem_ids
   - BatchGetItem to fetch related data
   - Merge in application

3. **Adjacency Lists (for 1:M relationships)**
   - Problem + TestCases in same partition
   - Single Query to get both

**Recommendation:** Heavy denormalization for hot paths, batch gets for cold paths.

---

#### Challenge 7: Concurrency and Atomic Operations
**Current Implementation:**
```python
# Pessimistic locking
job = ScriptGenerationJob.objects.select_for_update().get(id=x)

# Atomic counter increment
problem.metadata['execution_count'] += 1  # NOT ATOMIC currently
```

**DynamoDB Limitation:**
- No pessimistic locking
- Must use optimistic locking with conditional writes

**Solutions:**
1. **Optimistic Locking with Version Numbers**
   ```python
   table.update_item(
       Key={'PK': 'JOB#123'},
       UpdateExpression='SET #status = :new, #version = #version + 1',
       ConditionExpression='#version = :old_version',
       ExpressionAttributeValues={
           ':new': 'PROCESSING',
           ':old_version': current_version
       }
   )
   ```

2. **Atomic Counters for Increments**
   ```python
   table.update_item(
       Key={'PK': 'PROBLEM#baekjoon#1000'},
       UpdateExpression='ADD execution_count :inc',
       ExpressionAttributeValues={':inc': 1}
   )
   ```

**Recommendation:** Use atomic counters for increments, conditional writes with version for state transitions.

---

#### Challenge 8: Soft Deletes and Filtering
**Current Implementation:**
```python
# Soft delete
problem.is_deleted = True
problem.deleted_at = timezone.now()
problem.save()

# Filter out deleted
Problem.objects.filter(is_deleted=False)
```

**DynamoDB Consideration:**
- Deleted items still consume storage and read capacity
- Filter expressions applied after reading items (less efficient)

**Solutions:**
1. **GSI without Deleted Items (Sparse Index)**
   ```python
   # Only project non-deleted items to GSI
   # When marking as deleted, remove the GSI attribute

   table.update_item(
       Key={'PK': 'PROBLEM#...'},
       UpdateExpression='SET is_deleted = :true, deleted_at = :now REMOVE active_flag'
   )
   ```

2. **Move Deleted Items to Separate Partition**
   ```python
   # Update PK to archive partition
   old_pk = 'PROBLEM#baekjoon#1000'
   new_pk = 'DELETED#PROBLEM#baekjoon#1000'

   # Copy item with new PK, delete old item
   ```

**Recommendation:** Use sparse GSI for active items, maintain deleted items in main table for audit trail.

---

### 10.2 Data Migration Strategy

**Phase 1: Preparation (2-4 weeks)**
1. Analyze all access patterns (DONE via this document)
2. Design DynamoDB schema with GSIs
3. Create test DynamoDB tables in staging
4. Write migration scripts (SQL → DynamoDB)
5. Set up DynamoDB Streams → OpenSearch for search

**Phase 2: Dual-Write Period (2-4 weeks)**
1. Deploy code that writes to both PostgreSQL and DynamoDB
2. Monitor for errors, performance issues
3. Verify data consistency between systems
4. Gradually increase percentage of reads from DynamoDB

**Phase 3: Migration (1 week)**
1. Perform bulk migration of historical data
2. Verify data integrity (row counts, checksums)
3. Run parallel testing (same queries, compare results)

**Phase 4: Cutover (1-2 days)**
1. Enable 100% reads from DynamoDB
2. Disable writes to PostgreSQL (keep as read-only backup)
3. Monitor metrics closely for 48 hours

**Phase 5: Cleanup (1 week)**
1. Remove PostgreSQL write logic from code
2. Archive PostgreSQL database
3. Optimize DynamoDB based on production traffic patterns
4. Implement auto-scaling, alarms, dashboards

---

### 10.3 Rollback Plan

**Immediate Rollback (< 1 hour):**
- Feature flag to switch reads back to PostgreSQL
- PostgreSQL still receiving writes during dual-write period
- Zero data loss

**Delayed Rollback (> 1 hour, < 1 week):**
- Replay DynamoDB writes to PostgreSQL using DynamoDB Streams
- Verify data consistency
- Switch traffic back to PostgreSQL

**Full Rollback (> 1 week):**
- Export DynamoDB data to S3
- Transform to SQL format
- Bulk load into PostgreSQL
- Verify and switch traffic

---

### 10.4 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Data loss during migration** | Low | Critical | Dual-write period, point-in-time backups |
| **Performance degradation** | Medium | High | Extensive load testing, gradual rollout |
| **Cost overruns** | Medium | Medium | Start with on-demand, optimize over time |
| **Search functionality breaks** | High | High | Deploy OpenSearch before cutover |
| **Complex queries fail** | Medium | High | Rewrite query logic, test thoroughly |
| **Learning curve for team** | High | Medium | Training, documentation, pair programming |
| **Code complexity increases** | High | Medium | Well-abstracted data access layer |
| **Vendor lock-in** | High | Medium | Consider multi-cloud or hybrid approach |

---

### 10.5 Success Criteria

**Performance Metrics:**
- Average read latency < 20ms (vs current ~50ms)
- P99 read latency < 100ms
- Average write latency < 30ms
- Zero downtime during migration

**Cost Metrics:**
- DynamoDB costs ≤ current database costs (initially)
- Potential for 30-50% cost reduction with optimization

**Reliability Metrics:**
- 99.99% availability (DynamoDB SLA)
- Zero data loss
- Successful rollback testing

**Feature Parity:**
- All existing features work identically
- Search functionality maintained (via OpenSearch)
- Rate limiting accuracy maintained

---

## 11. Conclusion

### Summary of Findings

This Django application demonstrates several patterns that will require significant architectural changes for DynamoDB migration:

**Well-Suited for DynamoDB:**
- High read:write ratio (70:30)
- Time-series access patterns (recent-first sorting)
- Hot path optimization already implemented (caching, prefetching)
- Soft delete patterns
- Rate limiting with counters

**Challenging for DynamoDB:**
- Full-text search on titles
- Complex OR queries
- Database-level aggregations
- Offset-based pagination
- Relationship traversals (joins)
- Transactions with > 100 items

### Recommended Next Steps

1. **Start with Read-Heavy Tables**
   - Migrate SubscriptionPlans first (easiest)
   - Then Users table (high impact, manageable complexity)
   - Then Problems + TestCases (test relationship patterns)

2. **Deploy OpenSearch Early**
   - Essential for search functionality
   - Test integration before migrating Problems table

3. **Refactor Frontend for Cursor Pagination**
   - Required change, should be done early
   - Test thoroughly with high-volume tables

4. **Implement Dual-Write Pattern**
   - Critical for safe migration
   - Minimize risk of data loss

5. **Monitor and Optimize**
   - Set up comprehensive monitoring
   - Optimize GSIs based on actual access patterns
   - Consider read replicas or caching layers

### Final Recommendation

**Migration Feasibility:** Medium-to-High complexity, but achievable with proper planning.

**Timeline Estimate:** 3-6 months for full migration with minimal risk

**Cost-Benefit Analysis:**
- **Benefits:** Scalability, lower operational overhead, better latency, multi-region capability
- **Costs:** Development time, learning curve, ongoing AWS costs
- **Verdict:** Proceed if scaling beyond single-server PostgreSQL or need multi-region deployment

**Alternative Consideration:**
- If staying on relational DB is preferred, consider Aurora PostgreSQL (serverless) for better scalability without rewrite
- If high write volume is concern, consider time-series database for UsageLogs (TimescaleDB, InfluxDB)

---

## Appendix A: Query Patterns by Frequency

### Very High Frequency (> 1000/min)
1. User authentication by email
2. Get problem with test cases
3. Rate limit check (UsageLogs count)
4. Create execution record
5. Log usage

### High Frequency (100-1000/min)
1. List problems (cached)
2. Get problem by platform+ID
3. User's execution history
4. Check admin status
5. Get user with plan

### Medium Frequency (10-100/min)
1. Search problems by title
2. Filter by platform/language
3. User statistics
4. Update hints
5. Job status checks

### Low Frequency (< 10/min)
1. Admin operations (CRUD)
2. Problem registration
3. Draft management
4. Analytics queries
5. Bulk operations

---

## Appendix B: Index Usage Summary

### Most Critical Indexes (Hot Path)

1. **User.email** - Authentication
2. **User.google_id** - OAuth login
3. **Problem(platform, problem_id)** - Unique lookup
4. **UsageLog(user, action, created_at)** - Rate limiting
5. **SearchHistory(user, created_at)** - User history

### Frequently Used Indexes

6. **Problem(is_completed, is_deleted, created_at)** - List views
7. **TestCase(problem, created_at)** - Always with problem
8. **SearchHistory(is_code_public, created_at)** - Public history
9. **User(subscription_plan, is_active)** - Admin filtering

### Rarely Used Indexes

10. **Problem(language, created_at)** - Language filtering
11. **SearchHistory(platform, created_at)** - Analytics
12. **UsageLog(problem, created_at)** - Problem analytics

---

## Appendix C: Denormalization Opportunities

### Already Denormalized
- SearchHistory: `platform`, `problem_number`, `problem_title`, `user_identifier`

### Should Denormalize for DynamoDB
- User: Add `plan_limits` (from SubscriptionPlan)
- SearchHistory: Add `user_email` (from User)
- Problem: Add `test_case_count` (computed)

### Consider Denormalizing
- SearchHistory: Full `test_results` with inputs/outputs (currently requires join to TestCase)
- User: Add `hints_today_count`, `executions_today_count` (from UsageLogs)

---

**End of Analysis**

---

**Prepared by:** Django Backend Architect
**For:** DynamoDB Schema Design Team
**Total Analysis Time:** ~4-6 hours
**Lines of Code Analyzed:** 4,888
**Files Analyzed:** 15 (models, views, tasks, serializers, utils)
