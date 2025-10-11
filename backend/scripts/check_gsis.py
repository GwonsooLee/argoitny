#!/usr/bin/env python
"""Check existing GSIs in DynamoDB table"""
import boto3
import os

os.environ['LOCALSTACK_URL'] = 'http://localstack:4566'

dynamodb = boto3.client(
    'dynamodb',
    endpoint_url=os.getenv('LOCALSTACK_URL'),
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

table_name = 'algoitny_main'

try:
    response = dynamodb.describe_table(TableName=table_name)
    table_desc = response['Table']

    print(f"Table: {table_name}")
    print(f"Status: {table_desc['TableStatus']}")
    print(f"\nGlobal Secondary Indexes:")

    if 'GlobalSecondaryIndexes' in table_desc:
        for gsi in table_desc['GlobalSecondaryIndexes']:
            print(f"\n  - {gsi['IndexName']}")
            print(f"    KeySchema: {gsi['KeySchema']}")
            print(f"    Projection: {gsi['Projection']}")
    else:
        print("  No GSIs found")

except Exception as e:
    print(f"Error: {e}")
