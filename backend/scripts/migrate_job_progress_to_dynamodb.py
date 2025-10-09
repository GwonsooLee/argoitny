#!/usr/bin/env python
"""
Migrate JobProgressHistory from PostgreSQL to DynamoDB

This script migrates all existing job progress history entries from PostgreSQL
to DynamoDB while preserving timestamps and job associations.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import JobProgressHistory, ProblemExtractionJob, ScriptGenerationJob
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import JobProgressHistoryRepository
from django.contrib.contenttypes.models import ContentType


def migrate_job_progress_history():
    """Migrate all job progress history from PostgreSQL to DynamoDB"""

    print("=" * 70)
    print("Migrating JobProgressHistory from PostgreSQL to DynamoDB")
    print("=" * 70)
    print()

    # Initialize DynamoDB repository
    table = DynamoDBClient.get_table()
    progress_repo = JobProgressHistoryRepository(table)

    # Get content types
    extraction_ct = ContentType.objects.get_for_model(ProblemExtractionJob)
    generation_ct = ContentType.objects.get_for_model(ScriptGenerationJob)

    # Get all progress entries from PostgreSQL
    all_progress = JobProgressHistory.objects.all().order_by('created_at')
    total = all_progress.count()

    print(f"Found {total} job progress entries in PostgreSQL")
    print()

    migrated = 0
    skipped = 0
    errors = 0

    for progress in all_progress:
        try:
            # Determine job type
            if progress.content_type_id == extraction_ct.id:
                job_type = 'extraction'
            elif progress.content_type_id == generation_ct.id:
                job_type = 'generation'
            else:
                print(f"⚠️  Skipping unknown content type for job #{progress.object_id}")
                skipped += 1
                continue

            job_id = progress.object_id

            # Check if already exists in DynamoDB
            existing = progress_repo.get_progress_history(job_type, job_id, limit=1000)

            # Check if this specific entry exists (by step + timestamp)
            timestamp = int(progress.created_at.timestamp())
            already_exists = any(
                item['step'] == progress.step[:100] and
                abs(item['created_at'] - timestamp) < 2  # Within 2 seconds
                for item in existing
            )

            if already_exists:
                skipped += 1
                continue

            # Add to DynamoDB with original timestamp
            item = {
                'PK': f'JOB#{job_type}#{job_id}',
                'SK': f'PROG#{timestamp}',
                'tp': 'prog',
                'dat': {
                    'stp': progress.step[:100],
                    'msg': progress.message,
                    'sts': progress.status
                },
                'crt': timestamp
            }

            table.put_item(Item=item)
            migrated += 1

            if migrated % 10 == 0:
                print(f"Migrated {migrated}/{total} entries...", end='\r')

        except Exception as e:
            print(f"❌ Error migrating job #{progress.object_id}: {e}")
            errors += 1

    print()
    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Total entries in PostgreSQL: {total}")
    print(f"✅ Successfully migrated: {migrated}")
    print(f"⚠️  Skipped (already exists): {skipped}")
    print(f"❌ Errors: {errors}")
    print()

    # Verify migration
    print("=" * 70)
    print("Verification")
    print("=" * 70)

    # Count unique jobs in PostgreSQL
    pg_extraction_jobs = set(JobProgressHistory.objects.filter(
        content_type=extraction_ct
    ).values_list('object_id', flat=True))

    pg_generation_jobs = set(JobProgressHistory.objects.filter(
        content_type=generation_ct
    ).values_list('object_id', flat=True))

    print(f"PostgreSQL extraction jobs: {len(pg_extraction_jobs)}")
    print(f"PostgreSQL generation jobs: {len(pg_generation_jobs)}")
    print()

    # Check a few samples in DynamoDB
    print("Sample verification:")
    for job_id in list(pg_extraction_jobs)[:3]:
        history = progress_repo.get_progress_history('extraction', job_id)
        print(f"  Extraction job #{job_id}: {len(history)} entries in DynamoDB")

    for job_id in list(pg_generation_jobs)[:3]:
        history = progress_repo.get_progress_history('generation', job_id)
        print(f"  Generation job #{job_id}: {len(history)} entries in DynamoDB")

    print()
    print("🎉 Migration complete!")
    print()


if __name__ == '__main__':
    migrate_job_progress_history()
