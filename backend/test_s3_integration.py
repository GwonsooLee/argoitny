#!/usr/bin/env python
"""Test S3 integration for large test cases"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.dynamodb.repositories.problem_repository import ProblemRepository


def test_s3_integration():
    """Test S3 integration with large test cases"""
    print("=" * 60)
    print("Testing S3 Integration for Large Test Cases")
    print("=" * 60)

    repo = ProblemRepository()

    # Test 1: Small test case (should go to DynamoDB)
    print("\n[Test 1] Adding small test case (should go to DynamoDB)...")
    small_input = "1 2 3"
    small_output = "6"

    try:
        result = repo.add_testcase(
            platform='test',
            problem_id='small_test',
            testcase_id='1',
            input_str=small_input,
            output_str=small_output
        )
        storage = result.get('dat', {}).get('storage', 'unknown')
        print(f"✓ Small test case added (storage: {storage})")
        assert storage == 'dynamodb', f"Expected 'dynamodb', got '{storage}'"
    except Exception as e:
        print(f"✗ Failed to add small test case: {e}")
        return False

    # Test 2: Large test case (should go to S3)
    print("\n[Test 2] Adding large test case (should go to S3)...")
    # Create a test case > 50KB
    large_input = "x" * 30000  # 30KB
    large_output = "y" * 30000  # 30KB (total > 50KB)

    try:
        result = repo.add_testcase(
            platform='test',
            problem_id='large_test',
            testcase_id='1',
            input_str=large_input,
            output_str=large_output
        )
        storage = result.get('dat', {}).get('storage', 'unknown')
        print(f"✓ Large test case added (storage: {storage})")
        assert storage == 's3', f"Expected 's3', got '{storage}'"

        if storage == 's3':
            s3_key = result.get('dat', {}).get('s3_key')
            size = result.get('dat', {}).get('size')
            compressed_size = result.get('dat', {}).get('compressed_size')
            print(f"  - S3 key: {s3_key}")
            print(f"  - Original size: {size:,} bytes")
            print(f"  - Compressed size: {compressed_size:,} bytes")
            print(f"  - Compression ratio: {(1 - compressed_size/size)*100:.1f}%")
    except Exception as e:
        print(f"✗ Failed to add large test case: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Retrieve large test case
    print("\n[Test 3] Retrieving large test case from S3...")
    try:
        testcases = repo.get_testcases(platform='test', problem_id='large_test')
        if len(testcases) > 0:
            retrieved_input = testcases[0]['input']
            retrieved_output = testcases[0]['output']

            # Verify data integrity
            assert retrieved_input == large_input, "Input data mismatch!"
            assert retrieved_output == large_output, "Output data mismatch!"
            print(f"✓ Large test case retrieved successfully")
            print(f"  - Input length: {len(retrieved_input):,} chars")
            print(f"  - Output length: {len(retrieved_output):,} chars")
        else:
            print("✗ No test cases found")
            return False
    except Exception as e:
        print(f"✗ Failed to retrieve large test case: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Clean up
    print("\n[Test 4] Cleaning up test data...")
    try:
        repo.delete_problem(platform='test', problem_id='small_test')
        repo.delete_problem(platform='test', problem_id='large_test')
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"✗ Failed to clean up: {e}")

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_s3_integration()
    sys.exit(0 if success else 1)
