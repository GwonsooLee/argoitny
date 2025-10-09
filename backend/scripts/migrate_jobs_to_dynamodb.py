#!/usr/bin/env python
"""
Migrate ScriptGenerationJob and ProblemExtractionJob from PostgreSQL to DynamoDB

This script migrates all existing job entries from PostgreSQL to DynamoDB
while preserving all fields and relationships.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import ScriptGenerationJob, ProblemExtractionJob
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    ScriptGenerationJobRepository,
    ProblemExtractionJobRepository
)


def migrate_script_generation_jobs():
    """Migrate all script generation jobs from PostgreSQL to DynamoDB"""

    print("=" * 70)
    print("Migrating ScriptGenerationJobs from PostgreSQL to DynamoDB")
    print("=" * 70)
    print()

    # Initialize DynamoDB repository
    table = DynamoDBClient.get_table()
    job_repo = ScriptGenerationJobRepository(table)

    # Get all jobs from PostgreSQL
    all_jobs = ScriptGenerationJob.objects.all().order_by('created_at')
    total = all_jobs.count()

    print(f"Found {total} script generation jobs in PostgreSQL")
    print()

    migrated = 0
    skipped = 0
    errors = 0

    for job in all_jobs:
        try:
            # Check if already exists in DynamoDB
            existing = job_repo.get_job(job.id)

            if existing:
                skipped += 1
                continue

            # Create in DynamoDB
            job_repo.create_job(
                job_id=job.id,
                platform=job.platform,
                problem_id=job.problem_id,
                title=job.title,
                language=job.language,
                constraints=job.constraints,
                problem_url=job.problem_url or '',
                tags=job.tags or [],
                solution_code=job.solution_code or '',
                status=job.status
            )

            # Update with additional fields
            updates = {
                'celery_task_id': job.celery_task_id or '',
                'generator_code': job.generator_code or '',
                'error_message': job.error_message or ''
            }
            job_repo.update_job(job.id, updates)

            migrated += 1

            if migrated % 10 == 0:
                print(f"Migrated {migrated}/{total} jobs...", end='\r')

        except Exception as e:
            print(f"❌ Error migrating job #{job.id}: {e}")
            errors += 1

    print()
    print()
    print("=" * 70)
    print("ScriptGenerationJob Migration Summary")
    print("=" * 70)
    print(f"Total jobs in PostgreSQL: {total}")
    print(f"✅ Successfully migrated: {migrated}")
    print(f"⚠️  Skipped (already exists): {skipped}")
    print(f"❌ Errors: {errors}")
    print()


def migrate_problem_extraction_jobs():
    """Migrate all problem extraction jobs from PostgreSQL to DynamoDB"""

    print("=" * 70)
    print("Migrating ProblemExtractionJobs from PostgreSQL to DynamoDB")
    print("=" * 70)
    print()

    # Initialize DynamoDB repository
    table = DynamoDBClient.get_table()
    job_repo = ProblemExtractionJobRepository(table)

    # Get all jobs from PostgreSQL
    all_jobs = ProblemExtractionJob.objects.all().order_by('created_at')
    total = all_jobs.count()

    print(f"Found {total} problem extraction jobs in PostgreSQL")
    print()

    migrated = 0
    skipped = 0
    errors = 0

    for job in all_jobs:
        try:
            # Check if already exists in DynamoDB
            existing = job_repo.get_job(job.id)

            if existing:
                skipped += 1
                continue

            # Create in DynamoDB
            job_repo.create_job(
                job_id=job.id,
                problem_url=job.problem_url,
                platform=job.platform,
                problem_id=job.problem_id,
                problem_identifier=job.problem_identifier,
                status=job.status
            )

            # Update with additional fields
            updates = {
                'celery_task_id': job.celery_task_id or '',
                'error_message': job.error_message or ''
            }
            job_repo.update_job(job.id, updates)

            migrated += 1

            if migrated % 10 == 0:
                print(f"Migrated {migrated}/{total} jobs...", end='\r')

        except Exception as e:
            print(f"❌ Error migrating job #{job.id}: {e}")
            errors += 1

    print()
    print()
    print("=" * 70)
    print("ProblemExtractionJob Migration Summary")
    print("=" * 70)
    print(f"Total jobs in PostgreSQL: {total}")
    print(f"✅ Successfully migrated: {migrated}")
    print(f"⚠️  Skipped (already exists): {skipped}")
    print(f"❌ Errors: {errors}")
    print()


def verify_migration():
    """Verify migration by comparing counts"""

    print("=" * 70)
    print("Verification")
    print("=" * 70)

    table = DynamoDBClient.get_table()
    sg_repo = ScriptGenerationJobRepository(table)
    pe_repo = ProblemExtractionJobRepository(table)

    # Count PostgreSQL jobs
    pg_sg_count = ScriptGenerationJob.objects.count()
    pg_pe_count = ProblemExtractionJob.objects.count()

    print(f"PostgreSQL ScriptGenerationJobs: {pg_sg_count}")
    print(f"PostgreSQL ProblemExtractionJobs: {pg_pe_count}")
    print()

    # Sample a few jobs from DynamoDB
    print("Sample verification (first 3 jobs of each type):")

    sg_jobs, _ = sg_repo.list_jobs(limit=3)
    print(f"  Found {len(sg_jobs)} ScriptGenerationJobs in DynamoDB")
    for job in sg_jobs:
        print(f"    - Job #{job['id']}: {job['platform']} {job['problem_id']} ({job['status']})")

    print()

    pe_jobs, _ = pe_repo.list_jobs(limit=3)
    print(f"  Found {len(pe_jobs)} ProblemExtractionJobs in DynamoDB")
    for job in pe_jobs:
        print(f"    - Job #{job['id']}: {job['platform']} {job['problem_id']} ({job['status']})")

    print()
    print("🎉 Migration complete!")
    print()


if __name__ == '__main__':
    migrate_script_generation_jobs()
    print()
    migrate_problem_extraction_jobs()
    print()
    verify_migration()
