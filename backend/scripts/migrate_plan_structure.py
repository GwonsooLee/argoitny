#!/usr/bin/env python3
"""
Migrate Plan items from old structure to new structure

Old structure:
  PK: PLAN#1, PLAN#2, PLAN#3
  SK: META

New structure:
  PK: PLAN (shared)
  SK: META#1, META#2, META#3
"""
import os
import sys
import django
import asyncio

# Add backend to path
sys.path.insert(0, '/Users/gwonsoolee/algoitny/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.async_client import AsyncDynamoDBClient


async def migrate_plans():
    """Migrate plan items from old to new structure"""
    print("=" * 70)
    print("Starting Plan Structure Migration")
    print("=" * 70)
    print()

    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)

        # Step 1: Scan for old structure plans
        print("Step 1: Finding old structure plans...")
        response = await table.scan(
            FilterExpression='#tp = :tp AND SK = :sk',
            ExpressionAttributeNames={
                '#tp': 'tp'
            },
            ExpressionAttributeValues={
                ':tp': 'plan',
                ':sk': 'META'
            }
        )

        old_plans = response.get('Items', [])
        print(f"  Found {len(old_plans)} plans with old structure\n")

        if not old_plans:
            print("✓ No old structure plans found. Migration not needed.")
            return

        # Step 2: Create new structure items
        print("Step 2: Creating new structure items...")
        for item in old_plans:
            # Extract plan_id from PK (format: PLAN#1)
            old_pk = item['PK']
            plan_id = old_pk.replace('PLAN#', '')

            print(f"  Migrating Plan #{plan_id}:")
            print(f"    Old: PK={old_pk}, SK=META")

            # Create new item with same data but new PK/SK
            new_item = item.copy()
            new_item['PK'] = 'PLAN'
            new_item['SK'] = f'META#{plan_id}'

            print(f"    New: PK=PLAN, SK=META#{plan_id}")

            # Write new item
            await table.put_item(Item=new_item)
            print(f"    ✓ Created new structure item")

        print()

        # Step 3: Verify new items
        print("Step 3: Verifying new structure items...")
        response = await table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={
                ':pk': 'PLAN',
                ':sk': 'META#'
            }
        )

        new_plans = response.get('Items', [])
        print(f"  Found {len(new_plans)} plans with new structure")

        for item in sorted(new_plans, key=lambda x: x['SK']):
            plan_name = item.get('dat', {}).get('nm', 'Unknown')
            print(f"    - {item['SK']}: {plan_name}")

        print()

        # Step 4: Delete old structure items
        print("Step 4: Deleting old structure items...")
        for item in old_plans:
            old_pk = item['PK']
            plan_id = old_pk.replace('PLAN#', '')

            print(f"  Deleting old item: PK={old_pk}, SK=META")
            await table.delete_item(
                Key={
                    'PK': old_pk,
                    'SK': 'META'
                }
            )
            print(f"    ✓ Deleted")

        print()

        # Step 5: Final verification
        print("Step 5: Final verification...")

        # Check no old items remain
        response = await table.scan(
            FilterExpression='#tp = :tp AND SK = :sk AND begins_with(PK, :pk)',
            ExpressionAttributeNames={
                '#tp': 'tp'
            },
            ExpressionAttributeValues={
                ':tp': 'plan',
                ':sk': 'META',
                ':pk': 'PLAN#'
            }
        )

        remaining_old = response.get('Items', [])
        if remaining_old:
            print(f"  ⚠ WARNING: {len(remaining_old)} old items still exist!")
        else:
            print(f"  ✓ No old structure items remain")

        # Verify new items
        response = await table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={
                ':pk': 'PLAN',
                ':sk': 'META#'
            }
        )

        final_plans = response.get('Items', [])
        print(f"  ✓ {len(final_plans)} plans with new structure")

        print()
        print("=" * 70)
        print("✓ Migration completed successfully!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  - Migrated: {len(old_plans)} plans")
        print(f"  - Old structure removed: {len(old_plans)} items")
        print(f"  - New structure created: {len(final_plans)} items")


if __name__ == '__main__':
    asyncio.run(migrate_plans())
