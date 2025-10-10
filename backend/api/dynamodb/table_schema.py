"""
DynamoDB table schema definition for AlgoItny

Single Table Design with optimized access patterns
Entities: User, Problem, SearchHistory, UsageLog, SubscriptionPlan, UserStats, Jobs

Access Pattern Optimizations:
- Removed expensive SCAN operations (list_users, get_users_by_plan, list_problems_needing_review)
- Added caching for list_active_users (10min TTL, 90% cost reduction)
- UsageLog with date-partitioned PK for efficient rate limiting (1-3ms latency, 0.5 RCU)
- UserStats for O(1) unique problem counting (125 RCU → 0.5 RCU)
- TTL-based auto-cleanup for usage logs (90 days)

GSI Usage:
- GSI1: User email lookup & user history queries (ALL projection)
- GSI2: Google OAuth & public timeline (KEYS_ONLY projection for cost efficiency)
- GSI3: Problem status index (ALL projection)
"""


def get_table_schema():
    """
    Get table schema for development/testing environment

    Returns table creation parameters for DynamoDB.
    For production schema, see: terraform/dynamodb/algoitny/prod_apnortheast2/main.tf
    """
    return {
        'TableName': 'algoitny_main',
        'KeySchema': [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}  # Sort key
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            # GSI1 attributes (User email lookup & user history queries)
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            # GSI2 attributes (Google OAuth & public history timeline)
            {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
            # GSI3 attributes (Problem status index - completed/draft)
            {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3SK', 'AttributeType': 'N'},
        ],
        'BillingMode': 'PAY_PER_REQUEST',  # On-demand billing for development
        'GlobalSecondaryIndexes': [
            {
                # GSI1: Multi-purpose index for user and history access patterns
                # Pattern 1: User email lookup (GSI1PK=EMAIL#{email}, GSI1SK=USR#{user_id})
                # Pattern 2: User history queries (GSI1PK=USER#{user_id}, GSI1SK=HIST#{timestamp})
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                # GSI2: Multi-purpose index for Google auth and public content
                # Pattern 1: Google OAuth (GSI2PK=GID#{google_id}, no SK needed)
                # Pattern 2: Public timeline (GSI2PK=PUBLIC#HIST, GSI2SK={timestamp})
                # Note: KEYS_ONLY projection for cost efficiency
                'IndexName': 'GSI2',
                'KeySchema': [
                    {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'KEYS_ONLY'}
            },
            {
                # GSI3: Problem status index (GSI3PK=STATUS#{status}, GSI3SK={timestamp})
                'IndexName': 'GSI3',
                'KeySchema': [
                    {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'StreamSpecification': {
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        'Tags': [
            {'Key': 'Environment', 'Value': 'development'},
            {'Key': 'Application', 'Value': 'algoitny'}
        ]
    }


def create_table(client):
    """
    Create DynamoDB table

    Args:
        client: boto3 DynamoDB client

    Returns:
        Response from create_table call
    """
    schema = get_table_schema()

    try:
        response = client.create_table(**schema)
        print(f"✓ Table '{schema['TableName']}' creation initiated")
        print(f"  Status: {response['TableDescription']['TableStatus']}")
        return response
    except client.exceptions.ResourceInUseException:
        print(f"✓ Table '{schema['TableName']}' already exists")
        return None
    except Exception as e:
        print(f"✗ Failed to create table: {e}")
        raise


def wait_for_table(client, table_name='algoitny_main', timeout=60):
    """
    Wait for table to be active

    Args:
        client: boto3 DynamoDB client
        table_name: Name of the table
        timeout: Maximum wait time in seconds
    """
    import time

    print(f"Waiting for table '{table_name}' to become active...")
    start_time = time.time()

    while True:
        try:
            response = client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']

            if status == 'ACTIVE':
                print(f"✓ Table '{table_name}' is now active")
                return True

            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"✗ Timeout waiting for table to become active")
                return False

            print(f"  Current status: {status} (elapsed: {int(elapsed)}s)")
            time.sleep(2)

        except Exception as e:
            print(f"✗ Error checking table status: {e}")
            return False


def delete_table(client, table_name='algoitny_main'):
    """
    Delete DynamoDB table (for testing)

    Args:
        client: boto3 DynamoDB client
        table_name: Name of the table
    """
    try:
        client.delete_table(TableName=table_name)
        print(f"✓ Table '{table_name}' deleted")
    except client.exceptions.ResourceNotFoundException:
        print(f"Table '{table_name}' does not exist")
    except Exception as e:
        print(f"✗ Failed to delete table: {e}")
        raise


def describe_table(client, table_name='algoitny_main'):
    """
    Get table description

    Args:
        client: boto3 DynamoDB client
        table_name: Name of the table

    Returns:
        Table description dict
    """
    try:
        response = client.describe_table(TableName=table_name)
        return response['Table']
    except client.exceptions.ResourceNotFoundException:
        print(f"Table '{table_name}' does not exist")
        return None
    except Exception as e:
        print(f"✗ Failed to describe table: {e}")
        raise
