#!/usr/bin/env python3
"""Script to undelete a problem"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/Users/gwonsoolee/algoitny/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.async_client import AsyncDynamoDBClient
import asyncio


async def undelete_problem(platform: str, problem_id: str):
    """Undelete a problem by removing is_deleted flag"""
    print(f"=== Undeleting problem: {platform}/{problem_id} ===\n")

    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)

        pk = f'PROB#{platform}#{problem_id}'

        # Get current item
        response = await table.get_item(
            Key={'PK': pk, 'SK': 'META'}
        )

        if 'Item' not in response:
            print(f"❌ Problem not found: {pk}")
            return

        item = response['Item']
        print(f"Current status:")
        print(f"  is_deleted: {item.get('is_deleted', False)}")
        print(f"  deleted_at: {item.get('deleted_at', 'N/A')}")
        print(f"  deleted_reason: {item.get('deleted_reason', 'N/A')}")

        if not item.get('is_deleted'):
            print(f"\n✅ Problem is not deleted, no action needed")
            return

        # Remove deletion flags
        print(f"\n🔄 Removing deletion flags...")
        await table.update_item(
            Key={'PK': pk, 'SK': 'META'},
            UpdateExpression='REMOVE is_deleted, deleted_at, deleted_reason'
        )

        print(f"✅ Problem undeleted successfully!")

        # Verify
        verify_response = await table.get_item(
            Key={'PK': pk, 'SK': 'META'}
        )
        verify_item = verify_response['Item']
        print(f"\nVerification:")
        print(f"  is_deleted: {verify_item.get('is_deleted', 'REMOVED')}")
        print(f"  Title: {verify_item.get('dat', {}).get('tit', 'N/A')}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python undelete_problem.py <platform> <problem_id>")
        print("Example: python undelete_problem.py codeforces 2149G")
        sys.exit(1)

    platform = sys.argv[1]
    problem_id = sys.argv[2]

    asyncio.run(undelete_problem(platform, problem_id))
