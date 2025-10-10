#!/usr/bin/env python
"""Check what keys exist for a specific problem in DynamoDB"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.client import DynamoDBClient

def check_problem_keys(platform, problem_id):
    """Check all items for a specific problem"""
    table = DynamoDBClient.get_table()

    # Try different PK formats
    pk_formats = [
        f'PROB#{platform}#{problem_id}',
        f'PROBLEM#{platform}#{problem_id}',
    ]

    print(f"\n=== Checking problem: {platform}/{problem_id} ===\n")

    for pk in pk_formats:
        print(f"Trying PK: {pk}")

        # Query all items with this PK
        response = table.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': pk}
        )

        items = response.get('Items', [])
        print(f"  Found {len(items)} items")

        for item in items:
            print(f"    - PK: {item['PK']}, SK: {item['SK']}")
            if 'tp' in item:
                print(f"      Type: {item['tp']}")
        print()

    # Also try scanning for items that contain the problem_id
    print(f"\nScanning for items containing '{problem_id}'...")
    response = table.scan(
        FilterExpression='contains(PK, :problem_id)',
        ExpressionAttributeValues={':problem_id': problem_id},
        Limit=10
    )

    items = response.get('Items', [])
    print(f"Found {len(items)} items:")
    for item in items:
        print(f"  - PK: {item['PK']}, SK: {item['SK']}")

if __name__ == '__main__':
    platform = sys.argv[1] if len(sys.argv) > 1 else 'codeforces'
    problem_id = sys.argv[2] if len(sys.argv) > 2 else '2149G'

    check_problem_keys(platform, problem_id)
