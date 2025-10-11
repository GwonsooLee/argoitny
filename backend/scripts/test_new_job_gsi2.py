#!/usr/bin/env python
"""Test that new jobs are created with GSI2 attributes"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['LOCALSTACK_URL'] = 'http://localstack:4566'

from api.utils.async_job_helper import AsyncJobHelper
from api.dynamodb.async_client import AsyncDynamoDBClient
from boto3.dynamodb.conditions import Attr


async def test_new_job_creation():
    print("\n=== Testing New Job Creation with GSI2 ===\n")

    # 1. Create a new job
    print("1. Creating new job for codeforces/1359C...")
    new_job = await AsyncJobHelper.create_script_generation_job(
        platform='codeforces',
        problem_id='1359C',
        title='Mixing Water',
        language='python',
        constraints='Test constraints',
        problem_url='https://codeforces.com/contest/1359/problem/C',
        tags=['binary search', 'math'],
        status='PENDING'
    )

    job_id = new_job['id']
    print(f"✓ Created job: {job_id}")
    print(f"  Platform: {new_job['platform']}")
    print(f"  Problem ID: {new_job['problem_id']}")
    print(f"  Status: {new_job['status']}")

    # 2. Verify GSI2 attributes in DynamoDB
    print(f"\n2. Checking GSI2 attributes in DynamoDB...")
    async with AsyncDynamoDBClient.get_resource() as resource:
        table = await resource.Table(AsyncDynamoDBClient._table_name)
        response = await table.get_item(
            Key={'PK': f'SGJOB#{job_id}', 'SK': 'META'}
        )
        item = response.get('Item')

        if item:
            gsi2pk = item.get('GSI2PK')
            gsi2sk = item.get('GSI2SK')

            if gsi2pk and gsi2sk:
                print(f"✓ GSI2 attributes found:")
                print(f"  GSI2PK: {gsi2pk}")
                print(f"  GSI2SK: {gsi2sk}")
            else:
                print(f"✗ GSI2 attributes MISSING:")
                print(f"  GSI2PK: {gsi2pk}")
                print(f"  GSI2SK: {gsi2sk}")
                print(f"\n  Available keys: {list(item.keys())}")
        else:
            print(f"✗ Job not found in DynamoDB")

    # 3. Verify job appears in list
    print(f"\n3. Checking if job appears in list...")
    jobs, _ = await AsyncJobHelper.list_script_generation_jobs(
        platform='codeforces',
        problem_id='1359C'
    )

    job_ids = [job['id'] for job in jobs]
    if job_id in job_ids:
        print(f"✓ Job appears in list (found {len(jobs)} total jobs)")
        for job in jobs:
            print(f"  - {job['id']}: {job['status']}")
    else:
        print(f"✗ Job NOT in list (found {len(jobs)} jobs)")
        print(f"  Job IDs in list: {job_ids}")

    # 4. Clean up - delete the test job
    print(f"\n4. Cleaning up test job...")
    await AsyncJobHelper.delete_script_generation_job(job_id)
    print(f"✓ Test job deleted")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_new_job_creation())
