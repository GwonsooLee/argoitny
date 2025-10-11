#!/usr/bin/env python
"""Check script generation jobs in DynamoDB"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, '/app')

# Set environment before importing Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.config.settings')
os.environ.setdefault('LOCALSTACK_URL', 'http://localstack:4566')

import django
django.setup()

from api.dynamodb.async_repositories import AsyncDynamoDBClient


async def check_jobs():
    """Check script generation jobs"""
    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)

        # Scan for all sgjob items
        response = await table.scan(
            FilterExpression='#tp = :tp',
            ExpressionAttributeNames={'#tp': 'tp'},
            ExpressionAttributeValues={':tp': 'sgjob'}
        )

        items = response.get('Items', [])
        print(f"Found {len(items)} script generation jobs")

        for item in items:
            job_id = item['PK'].replace('SGJOB#', '')
            dat = item.get('dat', {})
            print(f"\nJob ID: {job_id}")
            print(f"  Platform: {dat.get('plt')}")
            print(f"  Problem ID: {dat.get('pid')}")
            print(f"  Status: {dat.get('sts')}")
            print(f"  Created: {item.get('crt')}")
            print(f"  GSI1PK: {item.get('GSI1PK')}")
            print(f"  GSI1SK: {item.get('GSI1SK')}")


if __name__ == '__main__':
    asyncio.run(check_jobs())
