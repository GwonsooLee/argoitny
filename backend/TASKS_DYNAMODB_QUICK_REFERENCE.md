# Celery Tasks DynamoDB - Quick Reference

## Task Usage Examples

### 1. execute_code_task (DynamoDB Implementation)

**New Approach (Recommended):**
```python
from api.tasks import execute_code_task

# Execute with platform/problem_identifier
result = execute_code_task.delay(
    code="print(sum(map(int, input().split())))",
    language="python",
    platform="baekjoon",
    problem_identifier="1000",
    user_id=123,
    user_identifier="user@example.com",
    is_code_public=True
)

# Result format
{
    'status': 'COMPLETED',
    'execution_id': 1696789012345678,  # Timestamp-based ID
    'results': [
        {
            'test_case_id': '1',
            'input': '1 2',
            'expected': '3',
            'output': '3',
            'passed': True,
            'error': None,
            'status': 'success'
        }
    ],
    'summary': {
        'total': 3,
        'passed': 3,
        'failed': 0
    }
}
```

**Legacy Approach (Backward Compatible):**
```python
# Execute with numeric problem_id (falls back to Django ORM)
result = execute_code_task.delay(
    code="print('Hello')",
    language="python",
    problem_id=456,  # Django ORM Problem.id
    user_id=123,
    user_identifier="user@example.com",
    is_code_public=False
)
```

---

### 2. generate_hints_task (DynamoDB Implementation)

```python
from api.tasks import generate_hints_task

# Generate hints for a failed execution
result = generate_hints_task.delay(
    history_id=1696789012345678  # From execute_code_task result
)

# Result format
{
    'status': 'COMPLETED',
    'hints': [
        'Your code outputs a string instead of a number',
        'Try using sum() function to add the integers',
        'Remember to convert input to integers using map()'
    ],
    'message': 'Generated 3 hints successfully'
}
```

---

## DynamoDB Data Structures

### SearchHistory Item

```python
{
    'PK': 'HIST#1696789012345678',
    'SK': 'META',
    'tp': 'hist',
    'dat': {
        'uid': 123,                    # user_id
        'uidt': 'user@example.com',    # user_identifier
        'pid': 'baekjoon#1000',        # problem composite key
        'plt': 'baekjoon',             # platform
        'pno': '1000',                 # problem_number
        'ptt': 'A+B',                  # problem_title
        'lng': 'python',               # language
        'cod': 'print(...)',           # code
        'res': 'Passed',               # result_summary
        'psc': 3,                      # passed_count
        'fsc': 0,                      # failed_count
        'toc': 3,                      # total_count
        'pub': True,                   # is_code_public
        'trs': [                       # test_results
            {
                'tid': '1',            # test_case_id
                'out': '3',            # output
                'pas': True,           # passed
                'err': None,           # error
                'sts': 'success'       # status
            }
        ],
        'hnt': [                       # hints (optional)
            'Hint 1...',
            'Hint 2...'
        ]
    },
    'crt': 1696789012,                 # created timestamp
    'upd': 1696789012,                 # updated timestamp
    'GSI2PK': 'PUBLIC',                # (if public)
    'GSI2SK': 'HIST#1696789012'        # (if public)
}
```

---

## Repository Methods Used

### SearchHistoryRepository

```python
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import SearchHistoryRepository

table = DynamoDBClient.get_table()
repo = SearchHistoryRepository(table)

# Create history
repo.create_history(
    history_id=1696789012345678,
    history_data={
        'uid': 123,
        'uidt': 'user@example.com',
        'pid': 'baekjoon#1000',
        'plt': 'baekjoon',
        'pno': '1000',
        'ptt': 'A+B',
        'lng': 'python',
        'cod': 'print(...)',
        'res': 'Passed',
        'psc': 3,
        'fsc': 0,
        'toc': 3,
        'pub': True,
        'trs': [...]
    }
)

# Get history
history = repo.get_history(1696789012345678)

# Update hints
repo.update_hints(
    history_id=1696789012345678,
    hints=['Hint 1', 'Hint 2']
)
```

### ProblemRepository

```python
from api.dynamodb.repositories import ProblemRepository

table = DynamoDBClient.get_table()
repo = ProblemRepository(table)

# Get problem with test cases
problem = repo.get_problem_with_testcases(
    platform='baekjoon',
    problem_id='1000'
)

# Result format
{
    'platform': 'baekjoon',
    'problem_id': '1000',
    'title': 'A+B',
    'solution_code': 'base64_encoded_string',
    'language': 'python',
    'test_cases': [
        {
            'testcase_id': '1',
            'input': '1 2',
            'output': '3',
            'created_at': 1696789012
        }
    ],
    'metadata': {},
    'created_at': 1696789012,
    'updated_at': 1696789012
}

# Update problem metadata
repo.update_problem(
    platform='baekjoon',
    problem_id='1000',
    updates={
        'metadata': {
            'execution_count': 42
        }
    }
)
```

---

## Field Name Cheat Sheet

### SearchHistory Fields
```
Long Name           → Short Name
================================
user_id            → uid
user_identifier    → uidt
problem_id         → pid (composite: platform#problem_id)
platform           → plt
problem_number     → pno
problem_title      → ptt
language           → lng
code               → cod
result_summary     → res
passed_count       → psc
failed_count       → fsc
total_count        → toc
is_code_public     → pub
test_results       → trs
hints              → hnt
```

### Test Result Fields
```
Long Name           → Short Name
================================
test_case_id       → tid
output             → out
passed             → pas
error              → err
status             → sts
```

---

## Error Handling

### Common Errors

**Problem Not Found:**
```python
{
    'status': 'FAILED',
    'error': 'Problem not found: baekjoon/9999'
}
```

**No Test Cases:**
```python
{
    'status': 'FAILED',
    'error': 'No test cases available for this problem'
}
```

**History Not Found (Hints):**
```python
{
    'status': 'FAILED',
    'error': 'Search history not found'
}
```

**No Failures (Hints):**
```python
{
    'status': 'FAILED',
    'error': 'No failed test cases - hints not needed'
}
```

---

## Testing Commands

### Run Test Script
```bash
# From backend directory
python test_tasks_dynamodb.py
```

### Test Individual Tasks (Django Shell)
```python
# Start Django shell
python manage.py shell

# Test execute_code_task
from api.tasks import execute_code_task
result = execute_code_task(
    code="print(sum(map(int, input().split())))",
    language="python",
    platform="baekjoon",
    problem_identifier="1000",
    user_id=1,
    user_identifier="test@example.com",
    is_code_public=True
)
print(result)

# Test generate_hints_task
from api.tasks import generate_hints_task
result = generate_hints_task(history_id=1696789012345678)
print(result)
```

### Verify Data in DynamoDB
```python
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import SearchHistoryRepository

table = DynamoDBClient.get_table()
repo = SearchHistoryRepository(table)

# Get history
history = repo.get_history(1696789012345678)
print(history)

# Check fields
dat = history['dat']
print(f"User: {dat['uidt']}")
print(f"Problem: {dat['plt']}/{dat['pno']}")
print(f"Result: {dat['res']}")
print(f"Passed: {dat['psc']}/{dat['toc']}")
```

---

## Migration Checklist

- [x] execute_code_task migrated to DynamoDB
- [x] generate_hints_task migrated to DynamoDB
- [x] Short field names implemented
- [x] Backward compatibility maintained
- [x] Error handling preserved
- [x] Task signatures unchanged
- [ ] Integration tests passing
- [ ] Performance benchmarks completed
- [ ] Production deployment verified

---

## Performance Metrics

### Expected Improvements

| Metric                    | Before (Django ORM) | After (DynamoDB) | Improvement |
|---------------------------|---------------------|------------------|-------------|
| SearchHistory Create      | ~50-100ms           | ~10-20ms         | 5x faster   |
| SearchHistory Read        | ~30-60ms            | ~5-10ms          | 6x faster   |
| Problem + TestCases Read  | ~100-150ms          | ~15-25ms         | 6x faster   |
| Storage Size per History  | ~2-3KB              | ~1.5-2KB         | 30% smaller |

---

## Support & Troubleshooting

### Check DynamoDB Connection
```python
from api.dynamodb.client import DynamoDBClient

try:
    table = DynamoDBClient.get_table()
    print(f"Connected to: {table.name}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Enable Debug Logging
```python
import logging
logging.getLogger('api.tasks').setLevel(logging.DEBUG)
```

### Common Issues

1. **"Table not found"**: Ensure DynamoDB table is created
2. **"Invalid timestamp"**: Check system time synchronization
3. **"AccessDenied"**: Verify AWS credentials and IAM permissions
4. **"ValidationException"**: Check data types in repository methods

---

## Files Modified

- `/Users/gwonsoolee/algoitny/backend/api/tasks.py` (Main changes)
- Test script: `/Users/gwonsoolee/algoitny/backend/test_tasks_dynamodb.py`
- Documentation: `/Users/gwonsoolee/algoitny/backend/TASKS_DYNAMODB_MIGRATION_SUMMARY.md`
- Quick ref: `/Users/gwonsoolee/algoitny/backend/TASKS_DYNAMODB_QUICK_REFERENCE.md`
