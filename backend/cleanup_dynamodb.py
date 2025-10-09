#!/usr/bin/env python3
"""
DynamoDB Cleanup Script

Deletes all items except:
- Subscription plans (tp = 'plan')
- User authentication data (tp = 'usr')

Deleted item types:
- Problems (tp = 'prob')
- Test cases (tp = 'tc')
- Script generation jobs (tp = 'sgjob')
- Problem extraction jobs (tp = 'pejob')
- Job progress history (tp = 'prog')
- Search history (tp = 'shist')
- Usage logs (tp = 'ulog')
- Counters (tp = 'counter')
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.client import DynamoDBClient
from boto3.dynamodb.conditions import Attr
from collections import defaultdict
from typing import List, Dict, Any


# Item types to KEEP (do not delete)
KEEP_TYPES = {'plan', 'usr'}

# Item types we expect to DELETE
DELETE_TYPES = {'prob', 'tc', 'sgjob', 'pejob', 'prog', 'shist', 'ulog', 'counter'}


def scan_table() -> List[Dict[str, Any]]:
    """
    Scan the entire DynamoDB table and return all items.

    Returns:
        List of all items in the table
    """
    table = DynamoDBClient.get_table()
    items = []
    last_evaluated_key = None

    print("Scanning DynamoDB table...")

    while True:
        if last_evaluated_key:
            response = table.scan(ExclusiveStartKey=last_evaluated_key)
        else:
            response = table.scan()

        items.extend(response.get('Items', []))

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        print(f"  Scanned {len(items)} items so far...")

    print(f"Total items scanned: {len(items)}")
    return items


def categorize_items(items: List[Dict[str, Any]]) -> tuple:
    """
    Categorize items into keep and delete buckets.

    Args:
        items: List of all items

    Returns:
        Tuple of (items_to_keep, items_to_delete, stats)
    """
    items_to_keep = []
    items_to_delete = []
    stats = defaultdict(int)

    for item in items:
        item_type = item.get('tp', 'unknown')
        stats[item_type] += 1

        if item_type in KEEP_TYPES:
            items_to_keep.append(item)
        else:
            items_to_delete.append(item)

    return items_to_keep, items_to_delete, dict(stats)


def delete_items_batch(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Delete items in batches of 25 (DynamoDB limit).

    Args:
        items: List of items to delete

    Returns:
        Dictionary with deletion statistics by type
    """
    table = DynamoDBClient.get_table()
    deletion_stats = defaultdict(int)
    total_deleted = 0
    failed_deletions = []

    # Process in batches of 25
    batch_size = 25
    total_batches = (len(items) + batch_size - 1) // batch_size

    print(f"\nDeleting {len(items)} items in {total_batches} batches...")

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            with table.batch_writer() as writer:
                for item in batch:
                    try:
                        writer.delete_item(
                            Key={
                                'PK': item['PK'],
                                'SK': item['SK']
                            }
                        )
                        item_type = item.get('tp', 'unknown')
                        deletion_stats[item_type] += 1
                        total_deleted += 1
                    except Exception as e:
                        failed_deletions.append({
                            'PK': item['PK'],
                            'SK': item['SK'],
                            'error': str(e)
                        })

            print(f"  Batch {batch_num}/{total_batches} completed ({total_deleted} deleted)")

        except Exception as e:
            print(f"  ERROR in batch {batch_num}: {e}")
            failed_deletions.extend([
                {'PK': item['PK'], 'SK': item['SK'], 'error': 'Batch failed'}
                for item in batch
            ])

    if failed_deletions:
        print(f"\nWARNING: {len(failed_deletions)} items failed to delete")
        for failure in failed_deletions[:10]:  # Show first 10 failures
            print(f"  - PK={failure['PK']}, SK={failure['SK']}: {failure['error']}")
        if len(failed_deletions) > 10:
            print(f"  ... and {len(failed_deletions) - 10} more")

    return dict(deletion_stats)


def print_summary(stats: Dict[str, int], items_to_keep: List, items_to_delete: List, deletion_stats: Dict[str, int]):
    """
    Print summary of the cleanup operation.

    Args:
        stats: Statistics of all items by type
        items_to_keep: Items that were kept
        items_to_delete: Items that were deleted
        deletion_stats: Actual deletion statistics
    """
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)

    print("\nITEMS SCANNED BY TYPE:")
    for item_type, count in sorted(stats.items()):
        print(f"  {item_type:15s}: {count:6d}")
    print(f"  {'TOTAL':15s}: {sum(stats.values()):6d}")

    print("\nITEMS KEPT (NOT DELETED):")
    keep_stats = defaultdict(int)
    for item in items_to_keep:
        keep_stats[item.get('tp', 'unknown')] += 1

    for item_type, count in sorted(keep_stats.items()):
        print(f"  {item_type:15s}: {count:6d}")
    print(f"  {'TOTAL KEPT':15s}: {len(items_to_keep):6d}")

    print("\nITEMS DELETED:")
    for item_type, count in sorted(deletion_stats.items()):
        print(f"  {item_type:15s}: {count:6d}")
    print(f"  {'TOTAL DELETED':15s}: {sum(deletion_stats.values()):6d}")

    print("\n" + "="*80)


def main():
    """Main execution function."""
    # Check for --yes flag to skip confirmation
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv

    print("="*80)
    print("DynamoDB Cleanup Script")
    print("="*80)
    print("\nThis script will DELETE all items except:")
    print("  - Subscription plans (tp = 'plan')")
    print("  - User authentication data (tp = 'usr')")
    print("\n" + "="*80)

    # Step 1: Scan table
    items = scan_table()

    if not items:
        print("\nNo items found in the table. Nothing to delete.")
        return

    # Step 2: Categorize items
    items_to_keep, items_to_delete, stats = categorize_items(items)

    print("\n" + "-"*80)
    print("ITEMS BY TYPE:")
    for item_type, count in sorted(stats.items()):
        status = "KEEP" if item_type in KEEP_TYPES else "DELETE"
        print(f"  {item_type:15s}: {count:6d} items ({status})")
    print("-"*80)

    print(f"\nTotal items to KEEP:   {len(items_to_keep)}")
    print(f"Total items to DELETE: {len(items_to_delete)}")

    if not items_to_delete:
        print("\nNo items to delete. Exiting.")
        return

    # Step 3: Confirm deletion
    if not skip_confirmation:
        print("\n" + "="*80)
        response = input(f"\nAre you sure you want to DELETE {len(items_to_delete)} items? (yes/no): ")

        if response.lower() != 'yes':
            print("\nOperation cancelled.")
            return
    else:
        print("\n" + "="*80)
        print(f"\nAuto-confirming deletion of {len(items_to_delete)} items (--yes flag provided)")

    # Step 4: Delete items
    deletion_stats = delete_items_batch(items_to_delete)

    # Step 5: Print summary
    print_summary(stats, items_to_keep, items_to_delete, deletion_stats)

    print("\nCleanup completed successfully!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
