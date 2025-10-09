"""
Backfill GSI1 attributes for existing jobs in DynamoDB

This script adds GSI1PK and GSI1SK to existing job items that were created
before the GSI1 fix was implemented.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.client import DynamoDBClient
from boto3.dynamodb.conditions import Attr


def backfill_script_generation_jobs():
    """Backfill GSI1 for ScriptGenerationJob items"""
    table = DynamoDBClient.get_table()

    print("=" * 60)
    print("Backfilling GSI1 for ScriptGenerationJob items...")
    print("=" * 60)

    # Scan for all script generation jobs
    response = table.scan(
        FilterExpression=Attr('tp').eq('sgjob')
    )

    jobs = response.get('Items', [])
    total = len(jobs)
    updated = 0
    skipped = 0
    errors = 0

    print(f"Found {total} ScriptGenerationJob items")
    print()

    for job in jobs:
        job_id = job['PK'].replace('SGJOB#', '')
        status = job.get('dat', {}).get('sts', 'PENDING')
        created_at = job.get('crt', 0)

        # Check if GSI1 already exists
        if 'GSI1PK' in job and 'GSI1SK' in job:
            print(f"  SKIP: {job_id[:12]}... (GSI1 already exists)")
            skipped += 1
            continue

        try:
            # Update item to add GSI1 attributes
            table.update_item(
                Key={'PK': job['PK'], 'SK': job['SK']},
                UpdateExpression='SET GSI1PK = :gsi1pk, GSI1SK = :gsi1sk',
                ExpressionAttributeValues={
                    ':gsi1pk': f'SGJOB#STATUS#{status}',
                    ':gsi1sk': f'{created_at:020d}#{job_id}'  # Zero-padded timestamp + unique ID
                }
            )
            print(f"  ✅ {job_id[:12]}... | Status: {status}")
            updated += 1

        except Exception as e:
            print(f"  ❌ {job_id[:12]}... | Error: {str(e)}")
            errors += 1

    print()
    print(f"ScriptGenerationJob Summary:")
    print(f"  Total:   {total}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")
    print()

    return updated, skipped, errors


def backfill_problem_extraction_jobs():
    """Backfill GSI1 for ProblemExtractionJob items"""
    table = DynamoDBClient.get_table()

    print("=" * 60)
    print("Backfilling GSI1 for ProblemExtractionJob items...")
    print("=" * 60)

    # Scan for all problem extraction jobs
    response = table.scan(
        FilterExpression=Attr('tp').eq('pejob')
    )

    jobs = response.get('Items', [])
    total = len(jobs)
    updated = 0
    skipped = 0
    errors = 0

    print(f"Found {total} ProblemExtractionJob items")
    print()

    for job in jobs:
        job_id = job['PK'].replace('PEJOB#', '')
        status = job.get('dat', {}).get('sts', 'PENDING')
        created_at = job.get('crt', 0)

        # Check if GSI1 already exists
        if 'GSI1PK' in job and 'GSI1SK' in job:
            print(f"  SKIP: {job_id[:12]}... (GSI1 already exists)")
            skipped += 1
            continue

        try:
            # Update item to add GSI1 attributes
            table.update_item(
                Key={'PK': job['PK'], 'SK': job['SK']},
                UpdateExpression='SET GSI1PK = :gsi1pk, GSI1SK = :gsi1sk',
                ExpressionAttributeValues={
                    ':gsi1pk': f'PEJOB#STATUS#{status}',
                    ':gsi1sk': f'{created_at:020d}#{job_id}'  # Zero-padded timestamp + unique ID
                }
            )
            print(f"  ✅ {job_id[:12]}... | Status: {status}")
            updated += 1

        except Exception as e:
            print(f"  ❌ {job_id[:12]}... | Error: {str(e)}")
            errors += 1

    print()
    print(f"ProblemExtractionJob Summary:")
    print(f"  Total:   {total}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")
    print()

    return updated, skipped, errors


def main():
    """Run backfill for all job types"""
    print()
    print("=" * 60)
    print("GSI1 BACKFILL SCRIPT FOR JOBS")
    print("=" * 60)
    print()

    # Backfill ScriptGenerationJob
    sg_updated, sg_skipped, sg_errors = backfill_script_generation_jobs()

    # Backfill ProblemExtractionJob
    pe_updated, pe_skipped, pe_errors = backfill_problem_extraction_jobs()

    # Overall summary
    print("=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    print(f"Total Updated: {sg_updated + pe_updated}")
    print(f"Total Skipped: {sg_skipped + pe_skipped}")
    print(f"Total Errors:  {sg_errors + pe_errors}")
    print()

    if sg_errors + pe_errors == 0:
        print("✅ Backfill completed successfully!")
    else:
        print("⚠️  Backfill completed with errors")
    print()


if __name__ == '__main__':
    main()
