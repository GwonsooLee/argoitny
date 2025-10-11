#!/usr/bin/env python3
"""
Test DynamoDB Session Backend

This script tests the async DynamoDB session backend to ensure it works correctly.

Usage:
    # Setup Django environment
    cd backend
    DJANGO_SETTINGS_MODULE=config.settings LOCALSTACK_URL=http://localhost:4566 python scripts/test_session_backend.py
"""
import os
import sys
import asyncio
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from api.sessions.dynamodb import AsyncDynamoDBSessionStore, DynamoDBSessionStore


async def test_async_session():
    """Test async session operations using direct async methods"""
    print("\n" + "="*60)
    print("Testing Async DynamoDB Session Backend")
    print("="*60)

    # Create a new session
    print("\n1. Creating new session...")
    session = AsyncDynamoDBSessionStore()
    await session.create()
    session_key = session.session_key
    print(f"   ✓ Session created: {session_key}")

    # Set some data - use _session_cache directly for async
    print("\n2. Setting session data...")
    session._session_cache = {
        'user_id': 12345,
        'username': 'testuser',
        'is_authenticated': True
    }
    await session.save()
    print(f"   ✓ Session data saved")

    # Load session data
    print("\n3. Loading session data...")
    new_session = AsyncDynamoDBSessionStore(session_key=session_key)
    data = await new_session.load()
    print(f"   ✓ Session loaded: {data}")

    # Verify data
    print("\n4. Verifying session data...")
    assert data.get('user_id') == 12345, "user_id mismatch"
    assert data.get('username') == 'testuser', "username mismatch"
    assert data.get('is_authenticated') == True, "is_authenticated mismatch"
    print(f"   ✓ All data verified correctly")

    # Check existence
    print("\n5. Checking session existence...")
    exists = await new_session.exists(session_key)
    assert exists == True, "Session should exist"
    print(f"   ✓ Session exists: {exists}")

    # Update session
    print("\n6. Updating session data...")
    # Load first, then update
    update_session = AsyncDynamoDBSessionStore(session_key=session_key)
    current_data = await update_session.load()
    current_data['last_activity'] = 'test_action'
    update_session._session_cache = current_data
    await update_session.save()
    print(f"   ✓ Session updated")

    # Reload and verify
    print("\n7. Reloading and verifying update...")
    reload_session = AsyncDynamoDBSessionStore(session_key=session_key)
    reload_data = await reload_session.load()
    assert reload_data.get('last_activity') == 'test_action', "Update not saved"
    print(f"   ✓ Update verified: {reload_data.get('last_activity')}")

    # Delete session
    print("\n8. Deleting session...")
    await reload_session.delete(session_key)
    print(f"   ✓ Session deleted")

    # Verify deletion
    print("\n9. Verifying deletion...")
    exists_after = await reload_session.exists(session_key)
    assert exists_after == False, "Session should not exist"
    print(f"   ✓ Session no longer exists: {exists_after}")

    print("\n" + "="*60)
    print("✓ All async session tests passed!")
    print("="*60)


def test_sync_session():
    """Test sync session operations"""
    print("\n" + "="*60)
    print("Testing Sync DynamoDB Session Backend")
    print("="*60)

    # Create a new session
    print("\n1. Creating new session...")
    session = DynamoDBSessionStore()
    session.create()
    session_key = session.session_key
    print(f"   ✓ Session created: {session_key}")

    # Set some data
    print("\n2. Setting session data...")
    session['user_id'] = 67890
    session['username'] = 'syncuser'
    session.save()
    print(f"   ✓ Session data saved")

    # Load session data
    print("\n3. Loading session data...")
    new_session = DynamoDBSessionStore(session_key=session_key)
    data = new_session.load()
    print(f"   ✓ Session loaded: {data}")

    # Verify data
    print("\n4. Verifying session data...")
    assert data.get('user_id') == 67890, "user_id mismatch"
    assert data.get('username') == 'syncuser', "username mismatch"
    print(f"   ✓ All data verified correctly")

    # Check existence
    print("\n5. Checking session existence...")
    exists = new_session.exists(session_key)
    assert exists == True, "Session should exist"
    print(f"   ✓ Session exists: {exists}")

    # Delete session
    print("\n6. Deleting session...")
    new_session.delete(session_key)
    print(f"   ✓ Session deleted")

    # Verify deletion
    print("\n7. Verifying deletion...")
    exists_after = new_session.exists(session_key)
    assert exists_after == False, "Session should not exist"
    print(f"   ✓ Session no longer exists: {exists_after}")

    print("\n" + "="*60)
    print("✓ All sync session tests passed!")
    print("="*60)


async def test_session_expiry():
    """Test session expiry (simulated)"""
    print("\n" + "="*60)
    print("Testing Session Expiry")
    print("="*60)

    print("\n1. Creating session with short expiry...")
    session = AsyncDynamoDBSessionStore()
    await session.create()
    session_key = session.session_key
    session._session_cache = {'test_data': 'expires_soon'}

    # Set expiry to 2 seconds (for testing)
    session.set_expiry(2)
    await session.save()
    print(f"   ✓ Session created with 2s expiry: {session_key}")

    print("\n2. Verifying session exists...")
    exists_before = await session.exists(session_key)
    print(f"   ✓ Session exists: {exists_before}")

    print("\n3. Waiting 3 seconds for expiry...")
    await asyncio.sleep(3)

    print("\n4. Checking session after expiry...")
    new_session = AsyncDynamoDBSessionStore(session_key=session_key)
    data = await new_session.load()
    print(f"   ✓ Session data after expiry: {data}")
    print(f"   ✓ Should be empty dict (expired): {len(data) == 0}")

    # Clean up if not already deleted by expiry check
    try:
        await new_session.delete(session_key)
    except:
        pass

    print("\n" + "="*60)
    print("✓ Session expiry test completed!")
    print("="*60)


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "DynamoDB Session Backend Tests")
    print("="*70)

    try:
        # Test async operations
        await test_async_session()

        # Test sync operations
        test_sync_session()

        # Test expiry
        await test_session_expiry()

        print("\n" + "="*70)
        print(" "*25 + "✓ ALL TESTS PASSED!")
        print("="*70 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
