"""DynamoDB table schema definition"""


def get_table_schema():
    """
    Get table schema based on DYNAMODB_SINGLE_TABLE_DESIGN_V2.md

    Returns table creation parameters for DynamoDB
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
            # GSI1 attributes (Job status queries - email/google_id lookup)
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},  # String for job timestamps and user IDs
            # GSI2 attributes (Google ID lookup - HASH only, no RANGE key)
            {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
            # GSI3 attributes (Problem status index - completed/draft)
            {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3SK', 'AttributeType': 'N'},
        ],
        'BillingMode': 'PAY_PER_REQUEST',  # On-demand billing for development
        'GlobalSecondaryIndexes': [
            {
                # GSI1: User authentication by email/google_id
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                # GSI2: Google ID lookup (HASH only, no RANGE key)
                'IndexName': 'GSI2',
                'KeySchema': [
                    {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                # GSI3: Problem status index (completed/draft problems)
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
