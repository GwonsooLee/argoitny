#!/usr/bin/env python3
"""
Initialize Django DynamoDB Table

This script creates a dedicated DynamoDB table for Django-related data:
- Session storage
- Celery task results
- Cache (optional)

Table Structure:
    Table Name: algoitny_django
    PK (String): Partition key - e.g., SESSION#{key}, TASK#{id}, CACHE#{key}
    SK (String): Sort key - Usually 'META' or timestamp-based
    TTL: exp (Number) - Unix timestamp for automatic expiration

Usage:
    # For LocalStack (development)
    LOCALSTACK_URL=http://localhost:4566 python scripts/init_django_dynamodb.py

    # For AWS (production)
    python scripts/init_django_dynamodb.py
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError


def create_django_table(table_name: str = 'algoitny_django'):
    """
    Create Django-specific DynamoDB table

    Args:
        table_name: Name of the DynamoDB table
    """
    # Configure boto3 client
    localstack_url = os.getenv('LOCALSTACK_URL')

    if localstack_url:
        # LocalStack configuration
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=localstack_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        )
        print(f"Using LocalStack at {localstack_url}")
    else:
        # Production AWS configuration
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
        )
        print("Using AWS")

    try:
        # Check if table already exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if table_name in existing_tables:
            print(f"✓ Table '{table_name}' already exists")
            return True

        # Create table
        print(f"\nCreating table: {table_name}...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},   # Partition key
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}   # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'tp', 'AttributeType': 'S'},  # Type attribute for GSI
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'TypeIndex',
                    'KeySchema': [
                        {'AttributeName': 'tp', 'KeyType': 'HASH'},
                        {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            Tags=[
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'Purpose', 'Value': 'Django data storage'},
                {'Key': 'ManagedBy', 'Value': 'Script'}
            ]
        )

        # Wait for table to be created
        print("Waiting for table to be created...")
        table.wait_until_exists()

        print(f"✓ Table '{table_name}' created successfully!")
        print(f"\nTable structure:")
        print(f"  - Partition Key: PK (String)")
        print(f"  - Sort Key: SK (String)")
        print(f"  - GSI: TypeIndex (tp, SK)")
        print(f"  - Billing: PAY_PER_REQUEST")

        # Enable TTL
        print(f"\nEnabling TTL on 'exp' attribute...")
        client = dynamodb.meta.client
        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'exp'
            }
        )
        print("✓ TTL enabled for automatic data expiration")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"✓ Table '{table_name}' already exists")
            return True
        else:
            print(f"✗ Error creating table: {e}")
            return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def verify_table(table_name: str = 'algoitny_django'):
    """
    Verify table configuration

    Args:
        table_name: Name of the DynamoDB table
    """
    localstack_url = os.getenv('LOCALSTACK_URL')

    if localstack_url:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=localstack_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        )
    else:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
        )

    try:
        print(f"\n{'='*60}")
        print(f"Table Configuration: {table_name}")
        print(f"{'='*60}")

        table = dynamodb.Table(table_name)
        table.load()

        print(f"Status: {table.table_status}")
        print(f"Item count: {table.item_count}")
        print(f"Billing mode: {table.billing_mode_summary.get('BillingMode', 'N/A')}")

        print(f"\nKey Schema:")
        for key in table.key_schema:
            print(f"  - {key['AttributeName']}: {key['KeyType']}")

        print(f"\nGlobal Secondary Indexes:")
        for gsi in table.global_secondary_indexes or []:
            print(f"  - {gsi['IndexName']}")
            for key in gsi['KeySchema']:
                print(f"    - {key['AttributeName']}: {key['KeyType']}")

        # Check TTL
        client = dynamodb.meta.client
        ttl_response = client.describe_time_to_live(TableName=table_name)
        ttl_status = ttl_response.get('TimeToLiveDescription', {}).get('TimeToLiveStatus', 'N/A')
        print(f"\nTTL Status: {ttl_status}")

        print(f"\n✓ Table is ready for use")

    except Exception as e:
        print(f"✗ Error verifying table: {e}")


def seed_example_data(table_name: str = 'algoitny_django'):
    """
    Seed example data for testing

    Args:
        table_name: Name of the DynamoDB table
    """
    localstack_url = os.getenv('LOCALSTACK_URL')

    if localstack_url:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=localstack_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        )
    else:
        # Skip seeding in production
        print("\nSkipping example data seed in production")
        return

    try:
        table = dynamodb.Table(table_name)
        import time
        current_time = int(time.time())

        # Example session
        session_item = {
            'PK': 'SESSION#test-session-key-123',
            'SK': 'META',
            'tp': 'session',
            'dat': '{"user_id": 1, "is_authenticated": true}',
            'exp': current_time + 3600,  # Expires in 1 hour
            'crt': current_time,
            'upd': current_time
        }

        # Example task result
        task_item = {
            'PK': 'TASK#test-task-id-456',
            'SK': 'META',
            'tp': 'task_result',
            'dat': '{"status": "SUCCESS", "result": "Task completed"}',
            'exp': current_time + 86400,  # Expires in 24 hours
            'crt': current_time,
            'upd': current_time
        }

        table.put_item(Item=session_item)
        table.put_item(Item=task_item)

        print(f"\n✓ Seeded example data:")
        print(f"  - Session: SESSION#test-session-key-123")
        print(f"  - Task: TASK#test-task-id-456")

    except Exception as e:
        print(f"✗ Error seeding data: {e}")


if __name__ == '__main__':
    print("="*60)
    print("Django DynamoDB Table Initialization")
    print("="*60)

    table_name = os.getenv('DJANGO_DYNAMODB_TABLE_NAME', 'algoitny_django')

    # Create table
    success = create_django_table(table_name)

    if success:
        # Verify table
        import time
        print("\nWaiting 2 seconds for table to be fully ready...")
        time.sleep(2)
        verify_table(table_name)

        # Seed example data in development
        if os.getenv('LOCALSTACK_URL'):
            seed_example_data(table_name)

    sys.exit(0 if success else 1)
