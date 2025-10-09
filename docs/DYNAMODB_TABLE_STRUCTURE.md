# DynamoDB Table Structure

## Overview

AlgoItny uses a **single-table design** in DynamoDB for all entities. The table name is `algoitny_main`.

### Table Schema

```
Table Name: algoitny_main
Billing Mode: PAY_PER_REQUEST (On-demand)
```

**Primary Keys:**
- `PK` (Partition Key) - String
- `SK` (Sort Key) - String

**Global Secondary Indexes (GSIs):**
1. **GSI1** - User authentication and job status queries
   - `GSI1PK` (Hash) - String
   - `GSI1SK` (Range) - String

2. **GSI2** - Google ID lookup (HASH only)
   - `GSI2PK` (Hash) - String

3. **GSI3** - Problem status index
   - `GSI3PK` (Hash) - String
   - `GSI3SK` (Range) - Number

**Stream:** Enabled (NEW_AND_OLD_IMAGES)

---

## Entity Patterns

### 1. User

**Purpose:** Store user account information

**Structure:**
```
PK: USR#{user_id}
SK: META
tp: usr
dat: {
  em: email (string)
  nm: name (string)
  pic: picture URL (string)
  gid: google_id (string)
  plan: subscription_plan_id (number)
  act: is_active (boolean)
  stf: is_staff (boolean)
}
crt: created_timestamp (number)
upd: updated_timestamp (number)
GSI1PK: EMAIL#{email}
GSI1SK: USR#{user_id}
GSI2PK: GID#{google_id}  (optional, only if google_id exists)
```

**Access Patterns:**
1. Get user by ID: Query on PK=`USR#{user_id}`, SK=`META`
2. Get user by email: Query GSI1 where GSI1PK=`EMAIL#{email}`
3. Get user by Google ID: Query GSI2 where GSI2PK=`GID#{google_id}`
4. List all users: Scan with filter tp=`usr` (expensive, use sparingly)

**Example:**
```json
{
  "PK": "USR#12345",
  "SK": "META",
  "tp": "usr",
  "dat": {
    "em": "user@example.com",
    "nm": "John Doe",
    "pic": "https://example.com/pic.jpg",
    "gid": "google_oauth_id_123",
    "plan": 1,
    "act": true,
    "stf": false
  },
  "crt": 1696752000,
  "upd": 1696752000,
  "GSI1PK": "EMAIL#user@example.com",
  "GSI1SK": "USR#12345",
  "GSI2PK": "GID#google_oauth_id_123"
}
```

---

### 2. SubscriptionPlan

**Purpose:** Store subscription plan configuration

**Structure:**
```
PK: PLAN#{plan_id}
SK: META
tp: plan
dat: {
  nm: name (string)
  dsc: description (string)
  mh: max_hints_per_day (number, -1 = unlimited)
  me: max_executions_per_day (number, -1 = unlimited)
  mp: max_problems (number, -1 = unlimited)
  cva: can_view_all_problems (boolean)
  crp: can_register_problems (boolean)
  prc: price (number)
  act: is_active (boolean)
}
crt: created_timestamp (number)
upd: updated_timestamp (number)
```

**Access Patterns:**
1. Get plan by ID: Query on PK=`PLAN#{plan_id}`, SK=`META`
2. List all plans: Scan with filter tp=`plan` (only ~5 items, negligible cost)

**Example:**
```json
{
  "PK": "PLAN#1",
  "SK": "META",
  "tp": "plan",
  "dat": {
    "nm": "Free",
    "dsc": "Basic free plan",
    "mh": 5,
    "me": 10,
    "mp": -1,
    "cva": true,
    "crp": false,
    "prc": 0,
    "act": true
  },
  "crt": 1696752000,
  "upd": 1696752000
}
```

---

### 3. Problem

**Purpose:** Store coding problem metadata

**Structure:**
```
PK: PROB#{platform}#{problem_id}
SK: META
tp: prob
dat: {
  tit: title (string)
  url: problem_url (string)
  tag: tags (list of strings)
  sol: solution_code (base64 encoded string)
  lng: language (string)
  con: constraints (string)
  cmp: is_completed (boolean)
  tcc: test_case_count (number)
  del: is_deleted (boolean)
  ddt: deleted_at (number, optional)
  drs: deleted_reason (string, optional)
  nrv: needs_review (boolean)
  rvn: review_notes (string, optional)
  vrf: verified_by_admin (boolean)
  rvt: reviewed_at (number, optional)
  met: metadata (map, optional)
}
crt: created_timestamp (number)
upd: updated_timestamp (number)
GSI3PK: PROB#COMPLETED or PROB#DRAFT
GSI3SK: timestamp (number)
```

**Test Cases (stored in S3):**
- Test cases are stored in S3 for efficiency
- S3 Key: `testcases/{platform}/{problem_id}/testcases.json.gz`
- DynamoDB only stores metadata reference

**Access Patterns:**
1. Get problem: Query on PK=`PROB#{platform}#{problem_id}`, SK=`META`
2. List completed problems: Query GSI3 where GSI3PK=`PROB#COMPLETED`, sorted by GSI3SK
3. List draft problems: Query GSI3 where GSI3PK=`PROB#DRAFT`, sorted by GSI3SK
4. List problems needing review: Scan with filter nrv=true (expensive)

**Example:**
```json
{
  "PK": "PROB#baekjoon#1000",
  "SK": "META",
  "tp": "prob",
  "dat": {
    "tit": "A+B",
    "url": "https://www.acmicpc.net/problem/1000",
    "tag": ["math", "implementation"],
    "sol": "cHJpbnQoc3VtKG1hcChpbnQsIGlucHV0KCkuc3BsaXQoKSkpKQ==",
    "lng": "python",
    "con": "1 ≤ A, B ≤ 10",
    "cmp": true,
    "tcc": 3,
    "del": false,
    "nrv": false,
    "vrf": true
  },
  "crt": 1696752000,
  "upd": 1696752000,
  "GSI3PK": "PROB#COMPLETED",
  "GSI3SK": 1696752000
}
```

---

### 4. ScriptGenerationJob

**Purpose:** Track test case generator script creation jobs

**Structure:**
```
PK: SGJOB#{job_id}
SK: META
tp: sgjob
dat: {
  plt: platform (string)
  pid: problem_id (string)
  tit: title (string)
  url: problem_url (string)
  tag: tags (list of strings)
  lng: language (string)
  con: constraints (string)
  gen: generator_code (string)
  sts: status (PENDING|PROCESSING|COMPLETED|FAILED)
  tid: celery_task_id (string)
  err: error_message (string)
}
crt: created_timestamp (number)
upd: updated_timestamp (number)
GSI1PK: SGJOB#STATUS#{status}
GSI1SK: {timestamp:020d}#{job_id}
```

**Access Patterns:**
1. Get job by ID: Query on PK=`SGJOB#{job_id}`, SK=`META`
2. List jobs by status: Query GSI1 where GSI1PK=`SGJOB#STATUS#{status}`
3. Find stale jobs: Query GSI1 where GSI1PK=`SGJOB#STATUS#PROCESSING` with filter upd < cutoff

**Example:**
```json
{
  "PK": "SGJOB#550e8400-e29b-41d4-a716-446655440000",
  "SK": "META",
  "tp": "sgjob",
  "dat": {
    "plt": "baekjoon",
    "pid": "1000",
    "tit": "A+B",
    "url": "https://www.acmicpc.net/problem/1000",
    "tag": ["math"],
    "lng": "python",
    "con": "1 ≤ A, B ≤ 10",
    "gen": "import random\nfor _ in range(10): print(random.randint(1,10), random.randint(1,10))",
    "sts": "COMPLETED",
    "tid": "celery-task-123",
    "err": ""
  },
  "crt": 1696752000,
  "upd": 1696752100,
  "GSI1PK": "SGJOB#STATUS#COMPLETED",
  "GSI1SK": "00000001696752000#550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 5. ProblemExtractionJob

**Purpose:** Track problem extraction/scraping jobs

**Structure:**
```
PK: PEJOB#{job_id}
SK: META
tp: pejob
dat: {
  plt: platform (string)
  pid: problem_id (string)
  url: problem_url (string)
  pidt: problem_identifier (string, human-readable like "1520E")
  tit: title (string, optional)
  sts: status (PENDING|PROCESSING|COMPLETED|FAILED)
  tid: celery_task_id (string)
  err: error_message (string)
}
crt: created_timestamp (number)
upd: updated_timestamp (number)
GSI1PK: PEJOB#STATUS#{status}
GSI1SK: {timestamp:020d}#{job_id}
```

**Access Patterns:**
1. Get job by ID: Query on PK=`PEJOB#{job_id}`, SK=`META`
2. List jobs by status: Query GSI1 where GSI1PK=`PEJOB#STATUS#{status}`
3. Find stale jobs: Query GSI1 where GSI1PK=`PEJOB#STATUS#PROCESSING` with filter upd < cutoff

**Example:**
```json
{
  "PK": "PEJOB#660e8400-e29b-41d4-a716-446655440001",
  "SK": "META",
  "tp": "pejob",
  "dat": {
    "plt": "codeforces",
    "pid": "1520E",
    "url": "https://codeforces.com/problemset/problem/1520/E",
    "pidt": "1520E",
    "tit": "Arranging The Sheep",
    "sts": "COMPLETED",
    "tid": "celery-task-456",
    "err": ""
  },
  "crt": 1696752000,
  "upd": 1696752100,
  "GSI1PK": "PEJOB#STATUS#COMPLETED",
  "GSI1SK": "00000001696752000#660e8400-e29b-41d4-a716-446655440001"
}
```

---

### 6. JobProgressHistory

**Purpose:** Track progress steps for extraction and generation jobs

**Structure:**
```
PK: JOB#{job_type}#{job_id}
SK: PROG#{timestamp}
tp: prog
dat: {
  stp: step (string, max 100 chars)
  msg: message (string)
  sts: status (started|in_progress|completed|failed)
}
crt: created_timestamp (number)
```

**job_type:** `extraction` or `generation`

**Access Patterns:**
1. Get progress history: Query on PK=`JOB#{job_type}#{job_id}`, SK begins_with `PROG#`
2. Get latest progress: Query on PK with SK begins_with `PROG#`, ScanIndexForward=False, Limit=1

**Example:**
```json
{
  "PK": "JOB#extraction#660e8400-e29b-41d4-a716-446655440001",
  "SK": "PROG#1696752050",
  "tp": "prog",
  "dat": {
    "stp": "Fetching webpage",
    "msg": "Fetching problem page from URL...",
    "sts": "completed"
  },
  "crt": 1696752050
}
```

---

### 7. SearchHistory

**Purpose:** Store user's problem search/test history

**Structure:**
```
PK: EMAIL#{email}#SHIST#{platform}#{problem_number}
SK: HIST#{timestamp}
tp: shist
dat: {
  plat: platform (string)
  pnum: problem_number (string)
  ptitle: problem_title (string)
  code: user_code (string, optional)
  pub: is_code_public (boolean)
  hints: hints (list of strings, optional)
}
crt: created_timestamp (number)
GSI1PK: PUBLIC#HIST  (only if is_code_public=true)
GSI1SK: timestamp (string)
```

**Access Patterns:**
1. Get user's search history: Query on PK begins_with `EMAIL#{email}#SHIST#`
2. Get user's problem history: Query on PK=`EMAIL#{email}#SHIST#{platform}#{problem_number}`
3. Get public history: Query GSI1 where GSI1PK=`PUBLIC#HIST`
4. Count unique problems: Query all user's search history, extract unique platform#problem_number

**Example:**
```json
{
  "PK": "EMAIL#user@example.com#SHIST#baekjoon#1000",
  "SK": "HIST#1696752000000",
  "tp": "shist",
  "dat": {
    "plat": "baekjoon",
    "pnum": "1000",
    "ptitle": "A+B",
    "code": "print(sum(map(int, input().split())))",
    "pub": true,
    "hints": ["힌트1", "힌트2"]
  },
  "crt": 1696752000000,
  "GSI1PK": "PUBLIC#HIST",
  "GSI1SK": "1696752000000"
}
```

---

### 8. UsageLog

**Purpose:** Track usage for rate limiting (CRITICAL HOT PATH)

**Structure:**
```
PK: USR#{user_id}#ULOG#{date_YYYYMMDD}  (date-partitioned for efficiency)
    or EMAIL#{email}#ULOG#{date_YYYYMMDD}
SK: ULOG#{timestamp}#{action}
tp: ulog
dat: {
  act: action (hint|execution)
  pid: problem_id (number, optional)
  plat: platform (string, optional)
  pnum: problem_number (string, optional)
  met: metadata (map, optional)
}
crt: created_timestamp (number)
ttl: auto_delete_timestamp (90 days from creation)
```

**Access Patterns (CRITICAL for rate limiting):**
1. Check daily usage count: Query on PK=`USR#{user_id}#ULOG#{date}` with COUNT (1-3ms latency)
2. Log usage: PutItem (5-10ms latency)
3. Get usage logs: Query on PK=`USR#{user_id}#ULOG#{date}` (for debugging)

**Performance:**
- **check_rate_limit:** 1-3ms latency, 0.5 RCU (COUNT query only)
- **log_usage:** 5-10ms latency, 1 WCU
- **TTL:** Automatically deletes logs after 90 days

**Example:**
```json
{
  "PK": "USR#12345#ULOG#20251008",
  "SK": "ULOG#1696752000#hint",
  "tp": "ulog",
  "dat": {
    "act": "hint",
    "pid": 1000,
    "plat": "baekjoon",
    "pnum": "1000"
  },
  "crt": 1696752000,
  "ttl": 1704528000
}
```

---

## Field Name Conventions

To optimize storage and reduce costs, we use **short field names** in the `dat` attribute:

### Common Fields
- `crt` - created_at (timestamp)
- `upd` - updated_at (timestamp)
- `tp` - type (entity type)
- `dat` - data (main data container)
- `ttl` - time-to-live (auto-delete timestamp)

### User (`usr`)
- `em` - email
- `nm` - name
- `pic` - picture
- `gid` - google_id
- `plan` - subscription_plan_id
- `act` - is_active
- `stf` - is_staff

### SubscriptionPlan (`plan`)
- `nm` - name
- `dsc` - description
- `mh` - max_hints_per_day
- `me` - max_executions_per_day
- `mp` - max_problems
- `cva` - can_view_all_problems
- `crp` - can_register_problems
- `prc` - price
- `act` - is_active

### Problem (`prob`)
- `tit` - title
- `url` - problem_url
- `tag` - tags
- `sol` - solution_code (base64 encoded)
- `lng` - language
- `con` - constraints
- `cmp` - is_completed
- `tcc` - test_case_count
- `del` - is_deleted
- `ddt` - deleted_at
- `drs` - deleted_reason
- `nrv` - needs_review
- `rvn` - review_notes
- `vrf` - verified_by_admin
- `rvt` - reviewed_at
- `met` - metadata

### ScriptGenerationJob (`sgjob`)
- `plt` - platform
- `pid` - problem_id
- `tit` - title
- `url` - problem_url
- `tag` - tags
- `lng` - language
- `con` - constraints
- `gen` - generator_code
- `sts` - status
- `tid` - celery_task_id
- `err` - error_message

### ProblemExtractionJob (`pejob`)
- `plt` - platform
- `pid` - problem_id
- `url` - problem_url
- `pidt` - problem_identifier
- `tit` - title
- `sts` - status
- `tid` - celery_task_id
- `err` - error_message

### JobProgressHistory (`prog`)
- `stp` - step
- `msg` - message
- `sts` - status

### SearchHistory (`shist`)
- `plat` - platform
- `pnum` - problem_number
- `ptitle` - problem_title
- `code` - user_code
- `pub` - is_code_public
- `hints` - hints

### UsageLog (`ulog`)
- `act` - action
- `pid` - problem_id
- `plat` - platform
- `pnum` - problem_number
- `met` - metadata

---

## Performance Characteristics

### Hot Paths (Critical Operations)
1. **Rate Limiting Check:** 1-3ms (UsageLog COUNT query)
2. **User Authentication:** 5-10ms (User lookup by email via GSI1)
3. **Problem Fetch:** 5-10ms (Problem GetItem)

### Warm Paths
1. **List Completed Problems:** 10-20ms (GSI3 Query)
2. **Job Status Check:** 10-20ms (GSI1 Query)
3. **Search History:** 10-20ms (Query on PK)

### Cold Paths (Expensive Operations)
1. **List All Users:** Scan operation (use sparingly)
2. **List Problems Needing Review:** Scan with filter (expensive)

---

## Cost Optimization

### Storage Optimization
- **Short field names** reduce item size by ~30%
- **Base64 encoding** for solution code (efficient storage)
- **S3 for test cases** (large data offloaded from DynamoDB)
- **TTL on UsageLog** (auto-cleanup after 90 days)

### Query Optimization
- **Date-partitioned usage logs** for efficient daily queries
- **GSI projections:** ALL (trade storage for query speed)
- **COUNT queries** for rate limiting (no data transfer)

---

## Backup & Recovery

- **Streams Enabled:** NEW_AND_OLD_IMAGES for change data capture
- **Point-in-Time Recovery:** Recommended for production
- **Backup Strategy:** Daily automated backups via AWS Backup

---

## Migration Notes

All entities have been migrated from MySQL to DynamoDB. The application uses repository pattern for data access:

**Repository Files:**
- `backend/api/dynamodb/repositories/user_repository.py`
- `backend/api/dynamodb/repositories/subscription_plan_repository.py`
- `backend/api/dynamodb/repositories/problem_repository.py`
- `backend/api/dynamodb/repositories/script_generation_job_repository.py`
- `backend/api/dynamodb/repositories/problem_extraction_job_repository.py`
- `backend/api/dynamodb/repositories/job_progress_repository.py`
- `backend/api/dynamodb/repositories/search_history_repository.py`
- `backend/api/dynamodb/repositories/usage_log_repository.py`

**Table Schema:**
- `backend/api/dynamodb/table_schema.py`

**Initialization:**
- `backend/scripts/init_dynamodb.py`
