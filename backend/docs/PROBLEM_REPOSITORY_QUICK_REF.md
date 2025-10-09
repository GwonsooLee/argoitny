# ProblemRepository Quick Reference

## Initialization

```python
from api.dynamodb.repositories import ProblemRepository
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('algoitny_main')
repo = ProblemRepository(table)
```

## Method Quick Reference

### 1. `create_problem(platform, problem_id, problem_data)`
**Create a new problem**
```python
repo.create_problem('baekjoon', '1000', {
    'title': 'A+B',
    'tags': ['math'],
    'is_completed': True
})
```

### 2. `get_problem(platform, problem_id)`
**Get problem metadata only**
```python
problem = repo.get_problem('baekjoon', '1000')
# Returns: {title, tags, is_completed, ...}
```

### 3. `get_problem_with_testcases(platform, problem_id)`
**Get problem with all test cases**
```python
data = repo.get_problem_with_testcases('baekjoon', '1000')
# Returns: {title, tags, test_cases: [{testcase_id, input, output}, ...], ...}
```

### 4. `update_problem(platform, problem_id, updates)`
**Update specific fields**
```python
repo.update_problem('baekjoon', '1000', {
    'is_completed': True,
    'tags': ['math', 'easy']
})
```

### 5. `delete_problem(platform, problem_id)`
**Hard delete problem and all test cases**
```python
success = repo.delete_problem('baekjoon', '1000')
# Returns: True/False
```

### 6. `add_testcase(platform, problem_id, testcase_id, input_str, output_str)`
**Add a test case**
```python
repo.add_testcase('baekjoon', '1000', '1', '1 2', '3')
```

### 7. `get_testcases(platform, problem_id)`
**Get all test cases for a problem**
```python
testcases = repo.get_testcases('baekjoon', '1000')
# Returns: [{testcase_id, input, output}, ...]
```

### 8. `list_completed_problems(limit=100)`
**List completed problems**
```python
problems = repo.list_completed_problems(limit=50)
# Returns: [{platform, problem_id, title, ...}, ...]
```

### 9. `list_draft_problems(limit=100)`
**List draft/incomplete problems**
```python
drafts = repo.list_draft_problems(limit=50)
# Returns: [{platform, problem_id, title, needs_review, ...}, ...]
```

### 10. `list_problems_needing_review(limit=100)`
**List problems needing admin review**
```python
review_list = repo.list_problems_needing_review(limit=50)
# Returns: [{platform, problem_id, title, review_notes, ...}, ...]
```

### 11. `soft_delete_problem(platform, problem_id, reason='')`
**Soft delete (mark as deleted, preserve data)**
```python
repo.soft_delete_problem('baekjoon', '1000', 'Duplicate')
# Sets: is_deleted=True, deleted_at=timestamp, deleted_reason
```

## Common Patterns

### Create Problem with Test Cases
```python
# 1. Create problem
repo.create_problem('baekjoon', '1000', {
    'title': 'A+B',
    'tags': ['math'],
    'is_completed': False
})

# 2. Add test cases
testcases = [
    ('1', '1 2', '3'),
    ('2', '5 7', '12')
]
for tc_id, inp, out in testcases:
    repo.add_testcase('baekjoon', '1000', tc_id, inp, out)

# 3. Mark as completed
repo.update_problem('baekjoon', '1000', {'is_completed': True})
```

### Check and Update
```python
# Get problem
problem = repo.get_problem('baekjoon', '1000')

if problem and not problem['is_deleted']:
    # Update if not deleted
    repo.update_problem('baekjoon', '1000', {
        'verified_by_admin': True
    })
```

### Migration Example
```python
from api.models import Problem as PGProblem

for pg_problem in PGProblem.objects.all():
    # Create in DynamoDB
    repo.create_problem(
        pg_problem.platform,
        str(pg_problem.problem_id),
        {
            'title': pg_problem.title,
            'tags': pg_problem.tags or [],
            'is_completed': pg_problem.is_completed
        }
    )

    # Migrate test cases
    for tc in pg_problem.test_cases.all():
        repo.add_testcase(
            pg_problem.platform,
            str(pg_problem.problem_id),
            str(tc.id),
            tc.input,
            tc.output
        )
```

## Field Names Reference

### Long → Short Mapping (for storage)
- title → tit
- problem_url → url
- tags → tag
- solution_code → sol
- language → lng
- constraints → con
- is_completed → cmp
- is_deleted → del
- deleted_at → ddt
- deleted_reason → drs
- needs_review → nrv
- review_notes → rvn
- verified_by_admin → vrf
- reviewed_at → rvt
- metadata → met

### TestCase Fields
- input → inp
- output → out

## DynamoDB Keys

### Problem
- **PK**: `PROB#<platform>#<problem_id>`
- **SK**: `META`
- **Type**: `prob`

### TestCase
- **PK**: `PROB#<platform>#<problem_id>`
- **SK**: `TC#<testcase_id>`
- **Type**: `tc`

## Performance Tips

1. **Use `get_problem()` when test cases not needed** (faster, cheaper)
2. **Batch test case additions** for better performance
3. **Avoid scan operations** in hot paths (use for admin only)
4. **Cache frequently accessed problems** (Redis/Elasticache)
5. **Use conditional expressions** to prevent race conditions

## Error Handling

```python
try:
    problem = repo.get_problem('baekjoon', '1000')
    if not problem:
        raise NotFoundError("Problem not found")
    if problem.get('is_deleted'):
        raise DeletedError("Problem deleted")
except Exception as e:
    logger.error(f"DynamoDB error: {e}")
    raise
```

## Testing

```python
@mock_dynamodb
def test_problem_repository():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='algoitny_main',
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )

    repo = ProblemRepository(table)
    repo.create_problem('test', '1', {'title': 'Test'})
    problem = repo.get_problem('test', '1')
    assert problem['title'] == 'Test'
```

## Documentation

- **Full Usage Guide**: `PROBLEM_REPOSITORY_USAGE.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Design Spec**: `/Users/gwonsoolee/algoitny/DYNAMODB_SINGLE_TABLE_DESIGN_V2.md`
