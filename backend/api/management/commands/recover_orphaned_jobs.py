"""
Django management command to recover orphaned jobs

Usage:
    python manage.py recover_orphaned_jobs [--timeout 30] [--dry-run]

This command finds jobs that are stuck in PROCESSING state for longer than
the timeout period and marks them as FAILED so they can be retried.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import ProblemExtractionJob, ScriptGenerationJob
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Recover orphaned jobs that are stuck in PROCESSING state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout in minutes (default: 30). Jobs older than this will be marked as failed.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        dry_run = options['dry_run']

        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)

        self.stdout.write(self.style.WARNING(
            f"\n{'DRY RUN: ' if dry_run else ''}Looking for orphaned jobs...\n"
            f"Timeout: {timeout_minutes} minutes\n"
            f"Cutoff time: {cutoff_time}\n"
        ))

        # Find orphaned extraction jobs
        orphaned_extraction = ProblemExtractionJob.objects.filter(
            status='PROCESSING',
            updated_at__lt=cutoff_time
        )

        # Find orphaned generation jobs
        orphaned_generation = ScriptGenerationJob.objects.filter(
            status='PROCESSING',
            updated_at__lt=cutoff_time
        )

        extraction_count = orphaned_extraction.count()
        generation_count = orphaned_generation.count()

        if extraction_count == 0 and generation_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No orphaned jobs found!'))
            return

        # Display orphaned extraction jobs
        if extraction_count > 0:
            self.stdout.write(self.style.WARNING(
                f'\n📋 Found {extraction_count} orphaned extraction job(s):\n'
            ))
            for job in orphaned_extraction:
                age_minutes = (timezone.now() - job.updated_at).total_seconds() / 60
                self.stdout.write(
                    f'  • Job #{job.id}: {job.platform}/{job.problem_id}\n'
                    f'    Status: {job.status}\n'
                    f'    Last updated: {job.updated_at} ({age_minutes:.1f} minutes ago)\n'
                    f'    Task ID: {job.celery_task_id or "None"}\n'
                )

        # Display orphaned generation jobs
        if generation_count > 0:
            self.stdout.write(self.style.WARNING(
                f'\n📋 Found {generation_count} orphaned generation job(s):\n'
            ))
            for job in orphaned_generation:
                age_minutes = (timezone.now() - job.updated_at).total_seconds() / 60
                self.stdout.write(
                    f'  • Job #{job.id}: {job.platform}/{job.problem_id}\n'
                    f'    Status: {job.status}\n'
                    f'    Last updated: {job.updated_at} ({age_minutes:.1f} minutes ago)\n'
                    f'    Task ID: {job.celery_task_id or "None"}\n'
                )

        if dry_run:
            # Check how many would be deleted vs failed
            from api.models import Problem
            jobs_to_delete = 0
            jobs_to_fail = 0

            for job in orphaned_extraction:
                if not Problem.objects.filter(platform=job.platform, problem_id=job.problem_id).exists():
                    jobs_to_delete += 1
                else:
                    jobs_to_fail += 1

            self.stdout.write(self.style.WARNING(
                f'\n🔍 DRY RUN Summary:\n'
                f'   - Extraction jobs to delete (no Problem): {jobs_to_delete}\n'
                f'   - Extraction jobs to mark FAILED: {jobs_to_fail}\n'
                f'   - Generation jobs to mark FAILED: {generation_count}\n'
            ))
            return

        # Process extraction jobs: delete if Problem doesn't exist, otherwise mark as FAILED
        from api.models import Problem
        deleted_count = 0
        failed_count = 0
        updated_problems = 0

        for job in orphaned_extraction:
            try:
                problem = Problem.objects.get(
                    platform=job.platform,
                    problem_id=job.problem_id
                )
                # Problem exists - mark job as FAILED
                job.status = 'FAILED'
                job.error_message = f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
                job.save(update_fields=['status', 'error_message'])
                failed_count += 1

                # Update Problem metadata
                problem.metadata = {
                    **(problem.metadata or {}),
                    'extraction_status': 'FAILED',
                    'extraction_job_id': job.id,
                    'error_message': 'Job orphaned and automatically recovered'
                }
                problem.save(update_fields=['metadata'])
                updated_problems += 1
                logger.info(f"Marked job #{job.id} as FAILED and updated Problem {job.platform}/{job.problem_id}")

            except Problem.DoesNotExist:
                # Problem doesn't exist - delete the job
                job_id = job.id
                platform = job.platform
                problem_id = job.problem_id
                job.delete()
                deleted_count += 1
                logger.info(f"Deleted orphaned job #{job_id} (Problem {platform}/{problem_id} not found)")

        # Mark generation jobs as failed (always, since we don't have a Problem foreign key for generation jobs)
        updated_generation = orphaned_generation.update(
            status='FAILED',
            error_message=f'Job orphaned: No updates received for more than {timeout_minutes} minutes. Worker may have crashed or restarted.'
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully processed {extraction_count + generation_count} orphaned job(s):\n'
            f'   - Extraction jobs deleted (no Problem): {deleted_count}\n'
            f'   - Extraction jobs marked FAILED: {failed_count}\n'
            f'   - Problems updated: {updated_problems}\n'
            f'   - Generation jobs marked FAILED: {updated_generation}\n'
        ))
