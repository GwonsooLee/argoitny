# DynamoDB Item Size Limit Analysis

## Problem
`ValidationException: Item size has exceeded the maximum allowed size` when saving test cases in DynamoDB.

## Current Architecture

### Table Structure
- **Table Name**: `algoitny_main`
- **Keys**: PK (Partition), SK (Sort)
- **Limit**: 400 KB per item (DynamoDB hard limit)

### Test Case Storage Pattern
**Location**: `/Users/gwonsoolee/algoitny/backend/api/dynamodb/repositories/problem_repository.py`

Each test case is stored as a separate item:
```python
PK: 'PROB#{platform}#{problem_id}'
SK: 'TC#{testcase_id}'
tp: 'tc'
dat: {
    'inp': input_str,      # Test case input
    'out': output_str      # Expected output
}
```

### Where Test Cases Are Created
**Location**: `/Users/gwonsoolee/algoitny/backend/api/tasks.py` (lines 218-228)

```python
# Create test cases with successful results only using DynamoDB
created_count = 0
for idx, r in enumerate(r for r in test_results if r['status'] == 'success'):
    problem_repo.add_testcase(
        platform=job['platform'],
        problem_id=job['problem_id'],
        testcase_id=str(idx + 1),
        input_str=r['input'],
        output_str=r['output']
    )
    created_count += 1
```

The task generates **20 test cases** (line 157) which can result in large data volumes.

## Root Causes

1. **Large Test Inputs/Outputs**: Some problems have test cases with very large input/output strings
2. **Base64 Encoding Overhead**: Solution code is base64-encoded, adding ~33% size overhead
3. **No Size Validation**: No checks before writing to DynamoDB
4. **Multiple Test Cases**: 20 test cases per problem, each as a separate item

## Size Breakdown Example

For a single test case item:
- PK: `PROB#baekjoon#1234` (~20 bytes)
- SK: `TC#1` (~5 bytes)
- tp: `tc` (~5 bytes)
- dat.inp: Could be 1-100 KB (depending on problem)
- dat.out: Could be 1-100 KB (depending on problem)
- Metadata overhead: ~50 bytes

**Total per item**: Can easily exceed 100 KB for complex problems

With 20 test cases, if each test case approaches 20 KB, we hit the 400 KB limit.

## Files Requiring Updates

1. **Repository Layer** (handles DynamoDB operations):
   - `/Users/gwonsoolee/algoitny/backend/api/dynamodb/repositories/problem_repository.py`
   - Methods: `add_testcase()`, `get_testcases()`, `get_problem_with_testcases()`

2. **Task Layer** (generates and saves test cases):
   - `/Users/gwonsoolee/algoitny/backend/api/tasks.py`
   - Function: `generate_script_task()` (lines 218-228)
   - Function: `generate_outputs_task()` (lines 337-349)
   - Function: `execute_code_task()` (uses test cases)

3. **View Layer** (returns data to frontend):
   - `/Users/gwonsoolee/algoitny/backend/api/views/problems.py`
   - Class: `ProblemDetailView` (returns test cases)

4. **Serializer Layer** (formats API responses):
   - `/Users/gwonsoolee/algoitny/backend/api/serializers.py`
   - May need updates if response format changes

## Proposed Solutions (Awaiting Architect Guidance)

### Option 1: Compression
- Use gzip to compress test case data before storing
- Decompress when reading
- Pros: Simple, backward compatible with wrapper
- Cons: CPU overhead, still has 400 KB limit

### Option 2: Chunking
- Split large test cases into multiple items
- Example: `TC#1#CHUNK#0`, `TC#1#CHUNK#1`, etc.
- Pros: Handles unlimited size
- Cons: More complex, multiple queries

### Option 3: S3 Offloading
- Store large test cases in S3
- Store S3 reference in DynamoDB
- Pros: No size limits, cost-effective for large data
- Cons: Additional service dependency, more complex

### Option 4: Hybrid Approach (Recommended)
- Use compression for all test cases (reduces size by ~70%)
- Use S3 offloading for test cases that still exceed limits after compression
- Add size validation and automatic routing
- Pros: Best of both worlds, graceful degradation
- Cons: Most implementation complexity

## Size Calculations

DynamoDB item size includes:
- Attribute names and values
- Binary data is counted as-is
- UTF-8 strings: 1 byte per character (ASCII) or more for Unicode
- Numbers: Up to 21 bytes

**Example calculation for single test case**:
```
PK (20 bytes) + SK (10 bytes) + tp (5 bytes) +
dat.inp (20,000 bytes) + dat.out (20,000 bytes) +
overhead (50 bytes) = ~40 KB per test case
```

With 20 test cases: 40 KB × 20 = **800 KB total** → Exceeds 400 KB limit!

## Implementation Considerations

1. **Backward Compatibility**: Must handle existing uncompressed data
2. **Performance**: Compression/decompression should be fast (use gzip or zlib)
3. **Error Handling**: Graceful fallback when size limits are exceeded
4. **Testing**: Test with large test cases (100+ KB inputs)
5. **Monitoring**: Log when approaching size limits

## Next Steps

1. ✅ **Analysis Complete**: Identified root cause and affected files
2. ⏳ **Awaiting Design**: Waiting for dynamodb-architect agent recommendations
3. ⏳ **Implementation**: Will implement based on architect's design
4. ⏳ **Testing**: Validate with large test cases
5. ⏳ **Migration**: Handle existing data if schema changes

---

**Status**: Ready for architect review and design recommendations.
