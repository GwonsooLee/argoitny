#!/usr/bin/env python
"""Check actual item structure in DynamoDB"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.client import DynamoDBClient

def check_item_structure(platform, problem_id):
    """Check the actual structure of a problem item"""
    table = DynamoDBClient.get_table()

    pk = f'PROB#{platform}#{problem_id}'

    print(f"\n=== Checking item structure for: {pk} ===\n")

    # Get item
    response = table.get_item(
        Key={
            'PK': pk,
            'SK': 'META'
        }
    )

    if 'Item' in response:
        item = response['Item']
        print("Full item structure:")
        print(json.dumps(item, indent=2, default=str))

        print("\n\nTop-level keys:")
        for key in sorted(item.keys()):
            print(f"  - {key}: {type(item[key]).__name__}")
    else:
        print("Item not found!")

if __name__ == '__main__':
    platform = sys.argv[1] if len(sys.argv) > 1 else 'codeforces'
    problem_id = sys.argv[2] if len(sys.argv) > 2 else '2149G'

    check_item_structure(platform, problem_id)
