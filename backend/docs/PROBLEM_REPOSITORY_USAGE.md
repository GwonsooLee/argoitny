# ProblemRepository Usage Guide

## Overview

The `ProblemRepository` class provides a complete interface for managing Problem and TestCase entities in DynamoDB using the single-table design pattern defined in `DYNAMODB_SINGLE_TABLE_DESIGN_V2.md`.

## Entity Patterns

### Problem Entity
- **PK**: `PROB#<platform>#<problem_id>`
- **SK**: `META`
- **Type**: `prob`

### TestCase Entity
- **PK**: `PROB#<platform>#<problem_id>`
- **SK**: `TC#<testcase_id>`
- **Type**: `tc`

## Field Mapping

### Problem Fields (stored in `dat` map)

| Long Name | Short Name | Type | Description |
|-----------|------------|------|-------------|
| title | tit | string | Problem title |
| problem_url | url | string | URL to the problem |
| tags | tag | list | Problem tags |
| solution_code | sol | string | Solution code (base64 encoded) |
| language | lng | string | Programming language |
| constraints | con | string | Problem constraints |
| is_completed | cmp | boolean | Completion status |
| is_deleted | del | boolean | Deletion status |
| deleted_at | ddt | number | Deletion timestamp |
| deleted_reason | drs | string | Reason for deletion |
| needs_review | nrv | boolean | Review flag |
| review_notes | rvn | string | Review notes |
| verified_by_admin | vrf | boolean | Admin verification flag |
| reviewed_at | rvt | number | Review timestamp |
| metadata | met | map | Additional metadata |

### TestCase Fields (stored in `dat` map)

| Long Name | Short Name | Type | Description |
|-----------|------------|------|-------------|
| input | inp | string | Test case input |
| output | out | string | Expected output |

## Usage Examples

### 1. Initialize Repository

```python
import boto3
from api.dynamodb.repositories import ProblemRepository

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('algoitny_main')

# Create repository instance
problem_repo = ProblemRepository(table)
```

### 2. Create a Problem

```python
problem_data = {
    'title': 'A+B',
    'problem_url': 'https://www.acmicpc.net/problem/1000',
    'tags': ['math', 'implementation'],
    'solution_code': 'YSwgYiA9IG1hcChpbnQsIGlucHV0KCkuc3BsaXQoKSkKcHJpbnQoYSArIGIp',  # base64
    'language': 'python',
    'constraints': '1 <= A, B <= 10',
    'is_completed': True,
    'needs_review': False,
    'verified_by_admin': True
}

result = problem_repo.create_problem(
    platform='baekjoon',
    problem_id='1000',
    problem_data=problem_data
)

print(f"Created problem: {result}")
```

### 3. Get Problem (without test cases)

```python
problem = problem_repo.get_problem(
    platform='baekjoon',
    problem_id='1000'
)

if problem:
    print(f"Title: {problem['title']}")
    print(f"Tags: {problem['tags']}")
    print(f"Completed: {problem['is_completed']}")
else:
    print("Problem not found")
```

### 4. Add Test Cases

```python
# Add multiple test cases
testcases = [
    ('1', '1 2', '3'),
    ('2', '5 7', '12'),
    ('3', '10 -5', '5')
]

for tc_id, input_str, output_str in testcases:
    problem_repo.add_testcase(
        platform='baekjoon',
        problem_id='1000',
        testcase_id=tc_id,
        input_str=input_str,
        output_str=output_str
    )
    print(f"Added test case {tc_id}")
```

### 5. Get Problem with Test Cases

```python
problem_with_tc = problem_repo.get_problem_with_testcases(
    platform='baekjoon',
    problem_id='1000'
)

if problem_with_tc:
    print(f"Title: {problem_with_tc['title']}")
    print(f"Test Cases: {len(problem_with_tc['test_cases'])}")

    for tc in problem_with_tc['test_cases']:
        print(f"  TC {tc['testcase_id']}: {tc['input']} -> {tc['output']}")
```

### 6. Get Only Test Cases

```python
test_cases = problem_repo.get_testcases(
    platform='baekjoon',
    problem_id='1000'
)

for tc in test_cases:
    print(f"Test Case {tc['testcase_id']}:")
    print(f"  Input: {tc['input']}")
    print(f"  Output: {tc['output']}")
```

### 7. Update Problem

```python
# Update specific fields
updated = problem_repo.update_problem(
    platform='baekjoon',
    problem_id='1000',
    updates={
        'is_completed': True,
        'verified_by_admin': True,
        'reviewed_at': int(time.time()),
        'tags': ['math', 'implementation', 'easy']
    }
)

print(f"Updated problem: {updated}")
```

### 8. List Completed Problems

```python
completed_problems = problem_repo.list_completed_problems(limit=50)

print(f"Found {len(completed_problems)} completed problems:")
for problem in completed_problems:
    print(f"  {problem['platform']}/{problem['problem_id']}: {problem['title']}")
```

### 9. List Draft Problems

```python
draft_problems = problem_repo.list_draft_problems(limit=50)

print(f"Found {len(draft_problems)} draft problems:")
for problem in draft_problems:
    print(f"  {problem['platform']}/{problem['problem_id']}: {problem['title']}")
    print(f"    Needs Review: {problem['needs_review']}")
```

### 10. List Problems Needing Review

```python
review_problems = problem_repo.list_problems_needing_review(limit=50)

print(f"Found {len(review_problems)} problems needing review:")
for problem in review_problems:
    print(f"  {problem['platform']}/{problem['problem_id']}: {problem['title']}")
    if problem.get('review_notes'):
        print(f"    Notes: {problem['review_notes']}")
```

### 11. Soft Delete a Problem

```python
deleted = problem_repo.soft_delete_problem(
    platform='baekjoon',
    problem_id='1000',
    reason='Duplicate problem'
)

print(f"Soft deleted problem: {deleted}")
# Problem is marked as deleted but not removed from database
```

### 12. Hard Delete a Problem

```python
# This deletes the problem and ALL test cases permanently
success = problem_repo.delete_problem(
    platform='baekjoon',
    problem_id='1000'
)

if success:
    print("Problem and all test cases deleted successfully")
else:
    print("Failed to delete problem")
```

## Best Practices

### 1. Error Handling

```python
try:
    problem = problem_repo.get_problem('baekjoon', '1000')
    if not problem:
        # Handle not found case
        print("Problem not found")
    elif problem.get('is_deleted'):
        # Handle deleted problem
        print("Problem has been deleted")
    else:
        # Process problem
        print(f"Found: {problem['title']}")
except Exception as e:
    # Handle DynamoDB errors
    print(f"Error: {e}")
```

### 2. Batch Operations

```python
# When adding multiple test cases, batch them
testcases = [...]  # List of test cases

items = []
for tc_id, input_str, output_str in testcases:
    items.append({
        'PK': f'PROB#baekjoon#1000',
        'SK': f'TC#{tc_id}',
        'tp': 'tc',
        'dat': {'inp': input_str, 'out': output_str},
        'crt': int(time.time())
    })

# Use batch write for better performance
problem_repo.batch_write(items)
```

### 3. Conditional Updates

```python
# Update only if problem is not deleted
pk = f'PROB#baekjoon#1000'
sk = 'META'

try:
    updated = problem_repo.update_item(
        pk=pk,
        sk=sk,
        update_expression='SET dat.#cmp = :cmp, #upd = :upd',
        expression_attribute_values={
            ':cmp': True,
            ':upd': int(time.time()),
            ':del': False
        },
        expression_attribute_names={
            '#cmp': 'cmp',
            '#upd': 'upd',
            '#del': 'del'
        }
    )
    print("Updated successfully")
except Exception as e:
    print(f"Update failed: {e}")
```

### 4. Pagination for Large Lists

```python
# For large datasets, implement pagination
def get_all_completed_problems():
    all_problems = []
    limit = 100

    # Note: Scan doesn't support pagination with LastEvaluatedKey in this implementation
    # For production, enhance the scan method to support pagination
    problems = problem_repo.list_completed_problems(limit=limit)
    all_problems.extend(problems)

    return all_problems
```

## Performance Considerations

1. **GetItem vs Query**:
   - `get_problem()` uses GetItem (fastest, 0.5 RCU)
   - `get_problem_with_testcases()` uses Query (0.5 RCU × items)

2. **Scan Operations**:
   - `list_completed_problems()` uses Scan (expensive)
   - `list_draft_problems()` uses Scan (expensive)
   - `list_problems_needing_review()` uses Scan (expensive)
   - Use sparingly, consider GSI for frequent queries

3. **Cost Optimization**:
   - Fetch only what you need (use `get_problem()` instead of `get_problem_with_testcases()` if test cases not needed)
   - Batch operations when possible
   - Use conditional expressions to prevent unnecessary writes

## Migration from PostgreSQL

```python
# Example migration script
from api.models import Problem as PGProblem
from api.dynamodb.repositories import ProblemRepository

def migrate_problems():
    problem_repo = ProblemRepository(table)

    # Get all problems from PostgreSQL
    pg_problems = PGProblem.objects.prefetch_related('test_cases').all()

    for pg_problem in pg_problems:
        # Create problem in DynamoDB
        problem_data = {
            'title': pg_problem.title,
            'problem_url': pg_problem.problem_url,
            'tags': pg_problem.tags or [],
            'solution_code': pg_problem.solution_code or '',
            'language': pg_problem.language or '',
            'constraints': pg_problem.constraints or '',
            'is_completed': pg_problem.is_completed,
            'is_deleted': pg_problem.is_deleted,
            'needs_review': pg_problem.needs_review,
            'verified_by_admin': pg_problem.verified_by_admin
        }

        problem_repo.create_problem(
            platform=pg_problem.platform,
            problem_id=str(pg_problem.problem_id),
            problem_data=problem_data
        )

        # Migrate test cases
        for tc in pg_problem.test_cases.all():
            problem_repo.add_testcase(
                platform=pg_problem.platform,
                problem_id=str(pg_problem.problem_id),
                testcase_id=str(tc.id),
                input_str=tc.input,
                output_str=tc.output
            )

        print(f"Migrated: {pg_problem.platform}/{pg_problem.problem_id}")

# Run migration
migrate_problems()
```

## Testing

```python
import pytest
from moto import mock_dynamodb
import boto3

@mock_dynamodb
def test_create_and_get_problem():
    # Setup mock DynamoDB
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

    # Test repository
    repo = ProblemRepository(table)

    # Create problem
    problem_data = {
        'title': 'Test Problem',
        'is_completed': True
    }
    repo.create_problem('baekjoon', '1000', problem_data)

    # Get problem
    problem = repo.get_problem('baekjoon', '1000')
    assert problem is not None
    assert problem['title'] == 'Test Problem'
    assert problem['is_completed'] is True
```
