# Celery Tasks DynamoDB Migration Summary

## Overview
Updated `/Users/gwonsoolee/algoitny/backend/api/tasks.py` to use DynamoDB repositories instead of Django ORM for SearchHistory and Problem data access.

## Changes Made

### 1. **execute_code_task** - Fully Migrated to DynamoDB

**What Changed:**
- **Test Case Retrieval**: Now uses DynamoDB `ProblemRepository` to fetch problems and test cases
- **SearchHistory Creation**: Migrated from Django ORM to DynamoDB `SearchHistoryRepository`
- **Field Name Conversion**: Converts data to short field names for DynamoDB storage

**Key Implementation Details:**

```python
# Test case retrieval from DynamoDB
problem_repo = ProblemRepository(table)
problem_data = problem_repo.get_problem_with_testcases(
    platform=platform,
    problem_id=problem_identifier
)

# SearchHistory creation with short field names
history_data = {
    'uid': user_id,           # user_id
    'uidt': user_identifier,  # user_identifier
    'pid': f'{platform}#{problem_identifier}',  # problem composite key
    'plt': platform,          # platform
    'pno': problem_identifier, # problem_number
    'ptt': problem_title,     # problem_title
    'lng': language,          # language
    'cod': code,              # code
    'res': 'Passed' if failed_count == 0 else 'Failed',  # result_summary
    'psc': passed_count,      # passed_count
    'fsc': failed_count,      # failed_count
    'toc': len(test_cases),   # total_count
    'pub': is_code_public,    # is_code_public
    'trs': dynamodb_test_results  # test_results
}

# Test results with short field names
dynamodb_test_results = [{
    'tid': test_case_id,   # test_case_id
    'out': output,         # output
    'pas': passed,         # passed
    'err': error,          # error
    'sts': status          # status
}]
```

**Backward Compatibility:**
- Maintains support for legacy `problem_id` parameter (numeric ID)
- Falls back to Django ORM when legacy format is used
- Task signature unchanged - fully compatible with existing callers

**Benefits:**
- Single query to fetch problem with all test cases
- Smaller storage footprint with short field names
- Timestamp-based unique history IDs (microsecond precision)
- Updates problem execution count in DynamoDB metadata

---

### 2. **generate_hints_task** - Fully Migrated to DynamoDB

**What Changed:**
- **SearchHistory Retrieval**: Now uses DynamoDB `SearchHistoryRepository.get_history()`
- **Problem Retrieval**: Uses DynamoDB `ProblemRepository.get_problem()`
- **Hints Update**: Uses DynamoDB `SearchHistoryRepository.update_hints()`
- **Field Extraction**: Handles short field names from DynamoDB

**Key Implementation Details:**

```python
# Fetch history from DynamoDB
history_repo = SearchHistoryRepository(table)
history = history_repo.get_history(history_id)

# Extract fields from DynamoDB format
history_data = history.get('dat', {})
failed_count = history_data.get('fsc', 0)      # failed_count
hints = history_data.get('hnt')                # hints
code = history_data.get('cod', '')             # code
language = history_data.get('lng', '')         # language
test_results = history_data.get('trs', [])     # test_results
problem_composite = history_data.get('pid', '') # problem composite key

# Convert test results from short to long field names for Gemini
failed_tests = []
for result in test_results:
    if not result.get('pas', True):  # pas = passed
        failed_tests.append({
            'test_case_id': result.get('tid'),
            'output': result.get('out', ''),
            'passed': result.get('pas', False),
            'error': result.get('err'),
            'status': result.get('sts', '')
        })

# Update hints in DynamoDB
history_repo.update_hints(history_id=history_id, hints=generated_hints)
```

**Backward Compatibility:**
- Task signature unchanged
- Returns same response format
- Handles base64-encoded solution codes

**Benefits:**
- No N+1 queries
- Direct DynamoDB access for faster reads
- Efficient updates with targeted field modification
- Minimal data transfer with short field names

---

### 3. **Tasks Not Migrated** (Still Using Django ORM)

The following tasks were **not migrated** as they use models that haven't been migrated to DynamoDB:

#### generate_script_task
- Still uses Django ORM for `ScriptGenerationJob`
- Uses DynamoDB for `Problem` and `TestCase` storage
- Hybrid approach: Job management in Django, data storage in DynamoDB

#### extract_problem_info_task
- Still uses Django ORM for `ProblemExtractionJob` and `JobProgressHistory`
- Uses DynamoDB for `Problem` storage
- Hybrid approach: Job tracking in Django, problem data in DynamoDB

#### generate_outputs_task
- Could be migrated but was not updated in this iteration
- Currently uses Django ORM

#### delete_job_task
- Uses Django ORM for `ScriptGenerationJob`
- No migration needed (job cleanup task)

#### recover_orphaned_jobs_task
- Uses Django ORM for job models
- Uses DynamoDB for problem metadata updates
- Hybrid approach for recovery operations

#### Cache warming tasks
- `warm_problem_cache_task`: Uses DynamoDB repositories
- `warm_user_stats_cache_task`: Still uses Django ORM (SearchHistory not fully migrated)
- `invalidate_cache_task`: No changes needed

---

## DynamoDB Short Field Name Mapping

### SearchHistory (dat field)
| Short | Long              | Type   | Description                    |
|-------|-------------------|--------|--------------------------------|
| uid   | user_id           | int    | User ID (nullable)             |
| uidt  | user_identifier   | string | User email/identifier          |
| pid   | problem_id        | string | Composite key: platform#problem|
| plt   | platform          | string | Platform name                  |
| pno   | problem_number    | string | Problem identifier             |
| ptt   | problem_title     | string | Problem title                  |
| lng   | language          | string | Programming language           |
| cod   | code              | string | User's submitted code          |
| res   | result_summary    | string | "Passed" or "Failed"           |
| psc   | passed_count      | int    | Number of passed tests         |
| fsc   | failed_count      | int    | Number of failed tests         |
| toc   | total_count       | int    | Total test cases               |
| pub   | is_code_public    | bool   | Public visibility flag         |
| trs   | test_results      | list   | Array of test result objects   |
| hnt   | hints             | list   | Array of hint strings          |

### Test Results (trs items)
| Short | Long              | Type   | Description              |
|-------|-------------------|--------|--------------------------|
| tid   | test_case_id      | string | Test case identifier     |
| out   | output            | string | Actual output            |
| pas   | passed            | bool   | Pass/fail status         |
| err   | error             | string | Error message (if any)   |
| sts   | status            | string | Execution status         |

---

## Testing Recommendations

### 1. Test execute_code_task
```python
# Test with new DynamoDB approach
result = execute_code_task.delay(
    code="print('Hello')",
    language="python",
    platform="baekjoon",
    problem_identifier="1000",
    user_id=1,
    user_identifier="user@example.com",
    is_code_public=True
)

# Test backward compatibility with legacy problem_id
result = execute_code_task.delay(
    code="print('Hello')",
    language="python",
    problem_id=123,  # Legacy numeric ID
    user_id=1,
    user_identifier="user@example.com",
    is_code_public=False
)
```

### 2. Test generate_hints_task
```python
# Create a test history with failed tests
history_id = 1234567890123456  # Timestamp-based ID

# Generate hints
result = generate_hints_task.delay(history_id)

# Verify hints are stored in DynamoDB
history = history_repo.get_history(history_id)
assert history['dat']['hnt'] is not None
```

### 3. Verify Data Format
```python
# Check SearchHistory structure in DynamoDB
{
    'PK': 'HIST#1234567890123456',
    'SK': 'META',
    'tp': 'hist',
    'dat': {
        'uid': 1,
        'uidt': 'user@example.com',
        'pid': 'baekjoon#1000',
        'plt': 'baekjoon',
        'pno': '1000',
        'ptt': 'A+B',
        'lng': 'python',
        'cod': 'print(sum(map(int, input().split())))',
        'res': 'Passed',
        'psc': 3,
        'fsc': 0,
        'toc': 3,
        'pub': True,
        'trs': [
            {'tid': '1', 'out': '3\n', 'pas': True, 'err': None, 'sts': 'success'},
            {'tid': '2', 'out': '7\n', 'pas': True, 'err': None, 'sts': 'success'}
        ]
    },
    'crt': 1696789012,
    'upd': 1696789012
}
```

---

## Migration Status Summary

| Task                        | DynamoDB Migration | Notes                                    |
|-----------------------------|--------------------|------------------------------------------|
| execute_code_task           | ✅ Complete        | Full DynamoDB for history + test cases   |
| generate_hints_task         | ✅ Complete        | Full DynamoDB for history + problem      |
| generate_script_task        | ⚠️ Partial         | Job in Django, data in DynamoDB          |
| extract_problem_info_task   | ⚠️ Partial         | Job in Django, problem in DynamoDB       |
| generate_outputs_task       | ❌ Not Started     | Could be migrated                        |
| delete_job_task             | ❌ N/A             | Job-only task (no migration needed)      |
| recover_orphaned_jobs_task  | ⚠️ Partial         | Hybrid Django + DynamoDB                 |
| warm_problem_cache_task     | ✅ Complete        | Uses DynamoDB repositories               |
| warm_user_stats_cache_task  | ❌ Not Started     | Still uses Django ORM                    |
| invalidate_cache_task       | ✅ Complete        | No changes needed                        |

---

## Performance Improvements

### Before (Django ORM)
- SearchHistory.objects.create() - Single insert with ORM overhead
- SearchHistory.objects.select_related('problem').get() - N+1 query risk
- Problem.objects.prefetch_related('test_cases').get() - Multiple queries

### After (DynamoDB)
- history_repo.create_history() - Direct DynamoDB put_item
- history_repo.get_history() - Single DynamoDB get_item
- problem_repo.get_problem_with_testcases() - Single DynamoDB query

### Storage Optimization
- **Before**: Full field names (e.g., "user_identifier", "problem_title")
- **After**: Short field names (e.g., "uidt", "ptt")
- **Estimated Savings**: ~30-40% reduction in storage size per history record

---

## Rollback Plan

If issues arise, you can revert to Django ORM by:

1. **Revert execute_code_task**: Use git to restore the previous version
2. **Update callers**: Ensure all callers use the old signature (problem_id only)
3. **Flush DynamoDB data**: Archive any data created during testing
4. **Switch back to Django models**: SearchHistory and TestCase models

---

## Next Steps

1. **Test Tasks Thoroughly**:
   - Run integration tests with real DynamoDB (LocalStack or AWS)
   - Verify task signatures are compatible with existing callers
   - Check Celery task results and error handling

2. **Monitor Performance**:
   - Track task execution times
   - Monitor DynamoDB read/write capacity
   - Check for any errors in Celery logs

3. **Migrate Remaining Tasks** (Optional):
   - `generate_outputs_task` - can be migrated to DynamoDB
   - `warm_user_stats_cache_task` - depends on full SearchHistory migration

4. **Update Views**:
   - Ensure API views that call these tasks pass correct parameters
   - Update any frontend code that interprets task results

---

## Important Notes

1. **History ID Generation**: Changed from Django auto-increment to timestamp-based (microsecond precision)
   - Ensures uniqueness across distributed systems
   - Compatible with DynamoDB partition keys
   - Old integer IDs still work for backward compatibility

2. **Error Handling**: Maintained all original error handling and retry logic
   - Tasks use same Celery decorators and retry strategies
   - Logging preserved for debugging

3. **Task Signatures**: Unchanged for backward compatibility
   - execute_code_task supports both new (platform/problem_identifier) and old (problem_id) formats
   - generate_hints_task signature unchanged

4. **Data Consistency**:
   - Problem metadata updates happen in DynamoDB
   - No dual writes to Django ORM and DynamoDB for migrated entities
   - Clean separation of concerns

---

## File Location
**Updated File**: `/Users/gwonsoolee/algoitny/backend/api/tasks.py`

**Related Files**:
- `/Users/gwonsoolee/algoitny/backend/api/dynamodb/repositories/search_history_repository.py`
- `/Users/gwonsoolee/algoitny/backend/api/dynamodb/repositories/problem_repository.py`
- `/Users/gwonsoolee/algoitny/backend/api/dynamodb/client.py`
