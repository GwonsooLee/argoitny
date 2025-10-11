#!/usr/bin/env python
"""Test API call to jobs endpoint"""
import asyncio
import httpx


async def test_api():
    """Test jobs API"""
    url = 'http://localhost:8000/api/register/jobs/'
    params = {
        'platform': 'codeforces',
        'problem_id': '1359C'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"\nJobs found: {len(data.get('jobs', []))}")
            for job in data.get('jobs', []):
                print(f"  - Job ID: {job.get('id')}")
                print(f"    Status: {job.get('status')}")
                print(f"    Created: {job.get('created_at')}")


if __name__ == '__main__':
    asyncio.run(test_api())
