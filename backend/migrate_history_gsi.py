#!/usr/bin/env python
"""
Migration script to add GSI1 indexes to existing HIST items

This script scans all HIST# items and adds GSI1PK and GSI1SK indexes
for items that don't have them yet.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.client import DynamoDBClient
from boto3.dynamodb.conditions import Attr
import time


def migrate_history_items():
    """Add GSI1 indexes to existing HIST items"""
    table = DynamoDBClient.get_table()

    print("🔍 Scanning for HIST items without GSI1 indexes...")

    # Scan for HIST items
    scan_kwargs = {
        'FilterExpression': Attr('PK').begins_with('HIST#') & Attr('SK').eq('META')
    }

    items_updated = 0
    items_skipped = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            history_id = item['PK'].replace('HIST#', '')
            dat = item.get('dat', {})

            # Extract user_id and timestamp
            user_id = dat.get('uid')
            # crt is in milliseconds
            timestamp_ms = item.get('crt')
            is_public = dat.get('pub', False)

            if not user_id or not timestamp_ms:
                print(f"⚠️  HIST#{history_id}: Missing uid or crt, skipping")
                items_skipped += 1
                continue

            # Build update expression
            update_parts = []
            expression_values = {}

            # Add GSI1 for user history queries (use milliseconds for proper sorting)
            update_parts.append('GSI1PK = :gsi1pk')
            update_parts.append('GSI1SK = :gsi1sk')
            expression_values[':gsi1pk'] = f'USER#{user_id}'
            expression_values[':gsi1sk'] = f'HIST#{timestamp_ms}'

            # Add GSI2 for public history if applicable
            if is_public:
                update_parts.append('GSI2PK = :gsi2pk')
                update_parts.append('GSI2SK = :gsi2sk')
                expression_values[':gsi2pk'] = 'PUBLIC#HIST'
                expression_values[':gsi2sk'] = str(timestamp_ms)

            # Update timestamp
            update_parts.append('upd = :upd')
            expression_values[':upd'] = int(time.time())

            update_expression = 'SET ' + ', '.join(update_parts)

            # Update item
            try:
                table.update_item(
                    Key={
                        'PK': f'HIST#{history_id}',
                        'SK': 'META'
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values
                )

                gsi2_status = " + GSI2" if is_public else ""
                print(f"✅ HIST#{history_id}: Updated GSI1{gsi2_status} indexes (user={user_id}, ts={timestamp_ms})")
                items_updated += 1
            except Exception as e:
                print(f"❌ HIST#{history_id}: Failed to update - {str(e)}")

        # Check if there are more items to scan
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
        scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

    print(f"\n📊 Migration complete:")
    print(f"   ✅ Updated: {items_updated}")
    print(f"   ⏭️  Skipped: {items_skipped}")
    print(f"   📝 Total: {items_updated + items_skipped}")


if __name__ == '__main__':
    print("🚀 Starting HIST GSI migration...")
    print("=" * 60)
    migrate_history_items()
    print("=" * 60)
    print("✨ Migration finished!")
