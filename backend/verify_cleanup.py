#!/usr/bin/env python3
"""
Verification script to check what's left in DynamoDB after cleanup.
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
from collections import defaultdict


def verify_remaining_items():
    """Scan table and show remaining items."""
    table = DynamoDBClient.get_table()
    response = table.scan()
    items = response.get('Items', [])

    print("="*80)
    print("VERIFICATION: Remaining Items in DynamoDB")
    print("="*80)
    print(f"\nTotal items remaining: {len(items)}\n")

    # Group by type
    by_type = defaultdict(list)
    for item in items:
        item_type = item.get('tp', 'unknown')
        by_type[item_type].append(item)

    # Show summary
    print("ITEMS BY TYPE:")
    print("-"*80)
    for item_type, type_items in sorted(by_type.items()):
        print(f"\n{item_type.upper()} ({len(type_items)} items):")
        for item in type_items[:5]:  # Show first 5 of each type
            pk = item.get('PK', 'N/A')
            sk = item.get('SK', 'N/A')
            print(f"  - PK: {pk:40s} SK: {sk}")
        if len(type_items) > 5:
            print(f"  ... and {len(type_items) - 5} more")

    print("\n" + "="*80)


if __name__ == '__main__':
    verify_remaining_items()
