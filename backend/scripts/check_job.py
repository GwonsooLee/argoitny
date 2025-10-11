#!/usr/bin/env python
"""Check if a specific job exists in DynamoDB"""
import asyncio
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('LOCALSTACK_URL', 'http://localstack:4566')

import django
django.setup()

from api.dynamodb.async_client import AsyncDynamoDBClient
from boto3.dynamodb.conditions import Attr


async def check_job():
    """Check for specific job"""
    job_id = 'b5a7b2c8-d63f-42da-82dd-c869e156e5fe'
    platform = 'codeforces'
    problem_id = '1359C'

    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)

        # Check by PK directly
        print(f"\n1. Checking job by PK: SGJOB#{job_id}")
        response = await table.get_item(Key={'PK': f'SGJOB#{job_id}', 'SK': 'META'})
        if response.get('Item'):
            item = response['Item']
            print(f"   ✓ Found job!")
            print(f"   Status: {item.get('dat', {}).get('sts')}")
            print(f"   Platform: {item.get('dat', {}).get('plt')}")
            print(f"   Problem ID: {item.get('dat', {}).get('pid')}")
            print(f"   Created: {item.get('crt')}")
        else:
            print(f"   ✗ Job not found")

        # Scan all sgjob items
        print(f"\n2. Scanning all script generation jobs:")
        response = await table.scan(
            FilterExpression=Attr('tp').eq('sgjob')
        )
        items = response.get('Items', [])
        print(f"   Found {len(items)} total jobs")

        for item in items:
            dat = item.get('dat', {})
            print(f"\n   Job: {item['PK']}")
            print(f"     Platform: {dat.get('plt')}")
            print(f"     Problem ID: {dat.get('pid')}")
            print(f"     Status: {dat.get('sts')}")

        # Filter by platform and problem_id
        print(f"\n3. Filtering jobs for {platform}/{problem_id}:")
        filtered = [
            item for item in items
            if item.get('dat', {}).get('plt') == platform
            and item.get('dat', {}).get('pid') == problem_id
        ]
        print(f"   Found {len(filtered)} matching jobs")
        for item in filtered:
            print(f"   - {item['PK']} (status: {item.get('dat', {}).get('sts')})")


if __name__ == '__main__':
    asyncio.run(check_job())
