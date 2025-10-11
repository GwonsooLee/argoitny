#!/usr/bin/env python3
"""
Enable TTL for DynamoDB sessions

This script enables Time-To-Live (TTL) on the DynamoDB table for automatic
session expiration. TTL removes expired sessions automatically without consuming
write capacity units.

Usage:
    # For LocalStack (development)
    LOCALSTACK_URL=http://localhost:4566 python scripts/enable_session_ttl.py

    # For AWS (production)
    python scripts/enable_session_ttl.py
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError


def enable_ttl(table_name: str = 'algoitny_main', ttl_attribute: str = 'exp'):
    """
    Enable TTL on DynamoDB table

    Args:
        table_name: Name of the DynamoDB table
        ttl_attribute: Name of the TTL attribute (default: 'exp')
    """
    # Configure boto3 client
    localstack_url = os.getenv('LOCALSTACK_URL')

    if localstack_url:
        # LocalStack configuration
        client = boto3.client(
            'dynamodb',
            endpoint_url=localstack_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        )
        print(f"Using LocalStack at {localstack_url}")
    else:
        # Production AWS configuration
        client = boto3.client(
            'dynamodb',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
        )
        print("Using AWS")

    try:
        # Check current TTL status
        print(f"\nChecking TTL status for table: {table_name}...")
        response = client.describe_time_to_live(TableName=table_name)

        ttl_status = response.get('TimeToLiveDescription', {}).get('TimeToLiveStatus')
        print(f"Current TTL status: {ttl_status}")

        if ttl_status == 'ENABLED':
            print(f"✓ TTL is already enabled on attribute: {ttl_attribute}")
            return True

        # Enable TTL
        print(f"\nEnabling TTL on attribute: {ttl_attribute}...")
        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': ttl_attribute
            }
        )

        print(f"✓ TTL enable request submitted successfully!")
        print(f"\nNote: It may take a few minutes for TTL to be fully enabled.")
        print(f"Sessions will expire automatically based on the '{ttl_attribute}' attribute.")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']

        if error_code == 'ResourceNotFoundException':
            print(f"✗ Error: Table '{table_name}' not found")
            print("\nPlease create the table first:")
            print("  - In LocalStack: docker-compose up -d && python scripts/init_dynamodb.py")
            print("  - In AWS: Deploy using Terraform")
        elif error_code == 'ValidationException':
            print(f"✗ Error: {e.response['Error']['Message']}")
        else:
            print(f"✗ Error: {e}")

        return False

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def verify_ttl_config(table_name: str = 'algoitny_main'):
    """
    Verify TTL configuration

    Args:
        table_name: Name of the DynamoDB table
    """
    localstack_url = os.getenv('LOCALSTACK_URL')

    if localstack_url:
        client = boto3.client(
            'dynamodb',
            endpoint_url=localstack_url,
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        )
    else:
        client = boto3.client(
            'dynamodb',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
        )

    try:
        print(f"\n{'='*60}")
        print(f"TTL Configuration for {table_name}")
        print(f"{'='*60}")

        response = client.describe_time_to_live(TableName=table_name)
        ttl_desc = response.get('TimeToLiveDescription', {})

        print(f"Status: {ttl_desc.get('TimeToLiveStatus', 'N/A')}")
        print(f"Attribute: {ttl_desc.get('AttributeName', 'N/A')}")

        if ttl_desc.get('TimeToLiveStatus') == 'ENABLED':
            print("\n✓ TTL is properly configured for automatic session expiration")
        else:
            print("\n⚠ TTL is not enabled. Run this script again to enable it.")

    except Exception as e:
        print(f"✗ Error verifying TTL config: {e}")


if __name__ == '__main__':
    print("="*60)
    print("DynamoDB Session TTL Configuration")
    print("="*60)

    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'algoitny_main')
    ttl_attribute = 'exp'

    print(f"\nTable: {table_name}")
    print(f"TTL Attribute: {ttl_attribute}")

    # Enable TTL
    success = enable_ttl(table_name, ttl_attribute)

    # Verify configuration
    if success:
        import time
        print("\nWaiting 2 seconds before verification...")
        time.sleep(2)
        verify_ttl_config(table_name)

    sys.exit(0 if success else 1)
