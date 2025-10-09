#!/usr/bin/env python3
"""
Initialize DynamoDB table in LocalStack or AWS

This script creates the main DynamoDB table with GSIs based on
DYNAMODB_SINGLE_TABLE_DESIGN_V2.md
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.dynamodb.client import DynamoDBClient
from api.dynamodb.table_schema import create_table, wait_for_table, describe_table


def main():
    """Initialize DynamoDB table"""
    print("=" * 60)
    print("DynamoDB Table Initialization")
    print("=" * 60)

    # Get environment info
    localstack_url = os.getenv('LOCALSTACK_URL')
    if localstack_url:
        print(f"✓ Environment: LocalStack ({localstack_url})")
    else:
        print(f"✓ Environment: AWS (region: {os.getenv('AWS_DEFAULT_REGION', 'us-east-1')})")

    print()

    # Get DynamoDB client
    client = DynamoDBClient.get_client()

    # Create table
    print("Creating DynamoDB table...")
    response = create_table(client)

    if response:
        # Wait for table to be active
        if wait_for_table(client, timeout=60):
            print()
            print("=" * 60)
            print("Table Details:")
            print("=" * 60)

            # Describe table
            table_info = describe_table(client)
            if table_info:
                print(f"Table Name: {table_info['TableName']}")
                print(f"Status: {table_info['TableStatus']}")
                print(f"Item Count: {table_info['ItemCount']}")
                print(f"Size (bytes): {table_info['TableSizeBytes']}")

                # GSI info
                gsis = table_info.get('GlobalSecondaryIndexes', [])
                print(f"\nGlobal Secondary Indexes: {len(gsis)}")
                for gsi in gsis:
                    print(f"  - {gsi['IndexName']}: {gsi['IndexStatus']}")

                print()
                print("✓ DynamoDB table initialized successfully!")
        else:
            print("\n✗ Table creation timed out")
            sys.exit(1)
    else:
        print("✓ Using existing table")

    print("=" * 60)


if __name__ == '__main__':
    main()
