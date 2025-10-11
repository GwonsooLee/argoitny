#!/usr/bin/env python3
"""
Test Celery DynamoDB Result Backend

This script tests the DynamoDB Celery result backend.

Usage:
    cd backend
    DJANGO_SETTINGS_MODULE=config.settings LOCALSTACK_URL=http://localhost:4566 python scripts/test_celery_backend.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from api.celery_backends.dynamodb import DynamoDBBackend
from celery import states, Celery


def test_celery_backend():
    """Test Celery DynamoDB backend"""
    print("\n" + "="*60)
    print("Testing Celery DynamoDB Result Backend")
    print("="*60)

    # Create Celery app
    app = Celery('test')

    # Create backend instance
    print("\n1. Creating backend instance...")
    backend = DynamoDBBackend(app=app)
    print(f"   ✓ Backend created: {backend.table_name}")
    print(f"   ✓ Result expiration: {backend.expires}s")

    # Store a successful task result
    print("\n2. Storing successful task result...")
    task_id = 'test-task-123'
    result = {'status': 'completed', 'data': [1, 2, 3]}
    backend._store_result(
        task_id=task_id,
        result=result,
        state=states.SUCCESS
    )
    print(f"   ✓ Result stored for task: {task_id}")

    # Retrieve task result
    print("\n3. Retrieving task result...")
    meta = backend._get_task_meta_for(task_id)
    print(f"   ✓ Task status: {meta['status']}")
    print(f"   ✓ Task result: {meta['result']}")
    assert meta['status'] == states.SUCCESS, "Status mismatch"
    assert meta['result'] == result, "Result mismatch"

    # Store a failed task result
    print("\n4. Storing failed task result...")
    failed_task_id = 'test-task-failed-456'
    error_msg = 'Task failed due to error'
    traceback_msg = 'Traceback: line 10 in test.py'
    backend._store_result(
        task_id=failed_task_id,
        result=error_msg,
        state=states.FAILURE,
        traceback=traceback_msg
    )
    print(f"   ✓ Failed result stored for task: {failed_task_id}")

    # Retrieve failed task result
    print("\n5. Retrieving failed task result...")
    failed_meta = backend._get_task_meta_for(failed_task_id)
    print(f"   ✓ Task status: {failed_meta['status']}")
    print(f"   ✓ Task result: {failed_meta['result']}")
    print(f"   ✓ Traceback: {failed_meta['traceback']}")
    assert failed_meta['status'] == states.FAILURE, "Status mismatch"
    assert failed_meta['result'] == error_msg, "Error message mismatch"
    assert failed_meta['traceback'] == traceback_msg, "Traceback mismatch"

    # Test non-existent task
    print("\n6. Testing non-existent task...")
    non_existent = backend._get_task_meta_for('non-existent-task')
    print(f"   ✓ Non-existent task status: {non_existent['status']}")
    assert non_existent['status'] == states.PENDING, "Should be PENDING"

    # Forget (delete) task result
    print("\n7. Forgetting task result...")
    backend._forget(task_id)
    print(f"   ✓ Task result deleted: {task_id}")

    # Verify deletion
    print("\n8. Verifying deletion...")
    deleted_meta = backend._get_task_meta_for(task_id)
    print(f"   ✓ Deleted task status: {deleted_meta['status']}")
    assert deleted_meta['status'] == states.PENDING, "Should be PENDING after deletion"

    # Clean up
    print("\n9. Cleaning up...")
    backend._forget(failed_task_id)
    print(f"   ✓ Cleanup complete")

    print("\n" + "="*60)
    print("✓ All Celery backend tests passed!")
    print("="*60)


if __name__ == '__main__':
    try:
        test_celery_backend()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
