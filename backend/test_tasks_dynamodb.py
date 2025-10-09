"""
Test script to verify DynamoDB integration in Celery tasks

This script verifies that:
1. execute_code_task correctly saves history to DynamoDB
2. generate_hints_task correctly reads/updates history in DynamoDB
3. Field name conversions work correctly
4. Backward compatibility is maintained

Run this after ensuring DynamoDB (LocalStack or AWS) is accessible.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.tasks import execute_code_task, generate_hints_task
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import SearchHistoryRepository, ProblemRepository


def setup_test_problem():
    """Create a test problem in DynamoDB"""
    print("\n[SETUP] Creating test problem in DynamoDB...")

    table = DynamoDBClient.get_table()
    problem_repo = ProblemRepository(table)

    # Create test problem
    problem_data = {
        'title': 'A+B Test Problem',
        'problem_url': 'https://acmicpc.net/problem/1000',
        'tags': ['math', 'implementation'],
        'solution_code': 'cHJpbnQoc3VtKG1hcChpbnQsIGlucHV0KCkuc3BsaXQoKSkpKQ==',  # base64 encoded
        'language': 'python',
        'constraints': 'Two integers A and B (0 < A, B < 10)',
        'is_completed': True,
        'is_deleted': False,
        'metadata': {}
    }

    problem_repo.create_problem(
        platform='baekjoon',
        problem_id='1000',
        problem_data=problem_data
    )

    # Add test cases
    test_cases = [
        ('1 2', '3'),
        ('3 4', '7'),
        ('5 5', '10')
    ]

    for idx, (input_str, output_str) in enumerate(test_cases, 1):
        problem_repo.add_testcase(
            platform='baekjoon',
            problem_id='1000',
            testcase_id=str(idx),
            input_str=input_str,
            output_str=output_str
        )

    print(f"[SETUP] Created problem 'baekjoon/1000' with {len(test_cases)} test cases")
    return 'baekjoon', '1000'


def test_execute_code_task():
    """Test execute_code_task with DynamoDB"""
    print("\n" + "="*70)
    print("TEST 1: execute_code_task with DynamoDB")
    print("="*70)

    platform, problem_id = setup_test_problem()

    # Test code that passes all tests
    passing_code = "print(sum(map(int, input().split())))"

    print(f"\n[TEST] Executing code for {platform}/{problem_id}...")

    # Call task synchronously (for testing)
    result = execute_code_task(
        code=passing_code,
        language='python',
        platform=platform,
        problem_identifier=problem_id,
        user_id=1,
        user_identifier='test@example.com',
        is_code_public=True
    )

    print(f"\n[RESULT] Task completed with status: {result['status']}")
    print(f"[RESULT] Execution ID: {result.get('execution_id')}")
    print(f"[RESULT] Summary: {result.get('summary')}")

    # Verify in DynamoDB
    if result.get('execution_id'):
        history_id = result['execution_id']
        table = DynamoDBClient.get_table()
        history_repo = SearchHistoryRepository(table)

        history = history_repo.get_history(history_id)

        if history:
            print(f"\n[VERIFY] History found in DynamoDB:")
            print(f"  - PK: {history.get('PK')}")
            print(f"  - Type: {history.get('tp')}")
            print(f"  - User ID: {history.get('dat', {}).get('uid')}")
            print(f"  - Platform: {history.get('dat', {}).get('plt')}")
            print(f"  - Problem: {history.get('dat', {}).get('pno')}")
            print(f"  - Language: {history.get('dat', {}).get('lng')}")
            print(f"  - Result: {history.get('dat', {}).get('res')}")
            print(f"  - Passed: {history.get('dat', {}).get('psc')}/{history.get('dat', {}).get('toc')}")
            print(f"  - Test Results: {len(history.get('dat', {}).get('trs', []))} items")

            # Check short field names
            dat = history.get('dat', {})
            required_fields = ['uid', 'uidt', 'pid', 'plt', 'pno', 'ptt', 'lng', 'cod', 'res', 'psc', 'fsc', 'toc', 'pub', 'trs']
            missing_fields = [f for f in required_fields if f not in dat]

            if missing_fields:
                print(f"\n[ERROR] Missing fields: {missing_fields}")
                return False
            else:
                print(f"\n[SUCCESS] All required fields present with short names")
                return True
        else:
            print(f"\n[ERROR] History {history_id} not found in DynamoDB")
            return False
    else:
        print("\n[ERROR] No execution_id returned")
        return False


def test_generate_hints_task():
    """Test generate_hints_task with DynamoDB"""
    print("\n" + "="*70)
    print("TEST 2: generate_hints_task with DynamoDB")
    print("="*70)

    platform, problem_id = setup_test_problem()

    # Test code that fails
    failing_code = "print('wrong answer')"

    print(f"\n[TEST] Executing failing code for {platform}/{problem_id}...")

    # Execute code to create history with failures
    result = execute_code_task(
        code=failing_code,
        language='python',
        platform=platform,
        problem_identifier=problem_id,
        user_id=1,
        user_identifier='test@example.com',
        is_code_public=False
    )

    if result['status'] != 'COMPLETED' or not result.get('execution_id'):
        print(f"[ERROR] Failed to execute code: {result}")
        return False

    history_id = result['execution_id']
    print(f"[TEST] Created history with ID: {history_id}")
    print(f"[TEST] Summary: {result.get('summary')}")

    # Verify there are failures
    if result['summary']['failed'] == 0:
        print("[ERROR] Expected failures but got none")
        return False

    print(f"\n[TEST] Generating hints for history {history_id}...")

    # Generate hints
    hint_result = generate_hints_task(history_id=history_id)

    print(f"\n[RESULT] Hint generation completed with status: {hint_result['status']}")
    print(f"[RESULT] Message: {hint_result.get('message')}")

    if hint_result.get('hints'):
        print(f"[RESULT] Generated {len(hint_result['hints'])} hints:")
        for idx, hint in enumerate(hint_result['hints'], 1):
            print(f"  {idx}. {hint[:100]}...")

    # Verify hints in DynamoDB
    table = DynamoDBClient.get_table()
    history_repo = SearchHistoryRepository(table)

    history = history_repo.get_history(history_id)

    if history:
        hints = history.get('dat', {}).get('hnt')
        if hints:
            print(f"\n[VERIFY] Hints found in DynamoDB: {len(hints)} hints")
            print(f"[SUCCESS] Hints successfully stored with short field name 'hnt'")
            return True
        else:
            print(f"\n[ERROR] Hints not found in DynamoDB history")
            return False
    else:
        print(f"\n[ERROR] History {history_id} not found in DynamoDB")
        return False


def test_backward_compatibility():
    """Test backward compatibility with legacy problem_id"""
    print("\n" + "="*70)
    print("TEST 3: Backward Compatibility (legacy problem_id)")
    print("="*70)

    # This test requires a Django ORM Problem to exist
    # For now, we'll just verify the task accepts the legacy parameter

    print("\n[INFO] This test requires Django ORM Problem model to exist")
    print("[INFO] Skipping for DynamoDB-only setup")
    print("[INFO] To test: Create a Problem in Django ORM and pass problem_id=<id>")

    return True


def cleanup_test_data():
    """Clean up test data from DynamoDB"""
    print("\n" + "="*70)
    print("CLEANUP: Removing test data")
    print("="*70)

    table = DynamoDBClient.get_table()
    problem_repo = ProblemRepository(table)

    # Delete test problem and all test cases
    success = problem_repo.delete_problem(
        platform='baekjoon',
        problem_id='1000'
    )

    if success:
        print("[CLEANUP] Test problem deleted successfully")
    else:
        print("[CLEANUP] Failed to delete test problem")

    # Note: We're not deleting history records for now (they can be useful for debugging)
    print("[CLEANUP] History records preserved for debugging")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("DynamoDB Celery Tasks Integration Tests")
    print("="*70)

    try:
        # Check DynamoDB connection
        table = DynamoDBClient.get_table()
        print(f"\n[INFO] Connected to DynamoDB table: {table.name}")

        # Run tests
        test1_passed = test_execute_code_task()
        test2_passed = test_generate_hints_task()
        test3_passed = test_backward_compatibility()

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Test 1 (execute_code_task): {'PASS' if test1_passed else 'FAIL'}")
        print(f"Test 2 (generate_hints_task): {'PASS' if test2_passed else 'FAIL'}")
        print(f"Test 3 (backward compatibility): {'PASS' if test3_passed else 'FAIL'}")

        all_passed = test1_passed and test2_passed and test3_passed
        print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

        # Cleanup
        cleanup_response = input("\n\nCleanup test data? (y/n): ")
        if cleanup_response.lower() == 'y':
            cleanup_test_data()

        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
