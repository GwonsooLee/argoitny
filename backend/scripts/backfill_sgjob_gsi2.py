#!/usr/bin/env python
"""Backfill GSI2PK/GSI2SK for existing ScriptGenerationJobs"""
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


async def backfill_gsi2():
    """Backfill GSI2PK/GSI2SK for all script generation jobs"""
    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)

        # Scan for all sgjob items
        print("Scanning for all script generation jobs...")
        response = await table.scan(
            FilterExpression=Attr('tp').eq('sgjob')
        )

        items = response.get('Items', [])
        print(f"Found {len(items)} jobs to update")

        updated_count = 0
        for item in items:
            job_id = item['PK'].replace('SGJOB#', '')
            dat = item.get('dat', {})
            platform = dat.get('plt')
            problem_id = dat.get('pid')
            created_at = item.get('crt', 0)

            if not platform or not problem_id:
                print(f"  ⚠️  Skipping {job_id}: missing platform or problem_id")
                continue

            # Check if GSI2PK already exists
            if item.get('GSI2PK'):
                print(f"  ✓ {job_id}: GSI2 already exists")
                continue

            # Update with GSI2PK/GSI2SK
            gsi2pk = f'SGJOB#{platform}#{problem_id}'
            created_at_int = int(created_at)  # Convert Decimal to int
            gsi2sk = f'{created_at_int:020d}#{job_id}'

            await table.update_item(
                Key={'PK': item['PK'], 'SK': item['SK']},
                UpdateExpression='SET GSI2PK = :gsi2pk, GSI2SK = :gsi2sk',
                ExpressionAttributeValues={
                    ':gsi2pk': gsi2pk,
                    ':gsi2sk': gsi2sk
                }
            )

            updated_count += 1
            print(f"  ✓ Updated {job_id}: GSI2PK={gsi2pk}")

        print(f"\n✅ Backfill complete! Updated {updated_count} jobs")


if __name__ == '__main__':
    asyncio.run(backfill_gsi2())
