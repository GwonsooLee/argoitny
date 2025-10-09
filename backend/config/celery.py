"""Celery configuration for AlgoItny project"""
import os
import logging
from celery import Celery
from celery.signals import worker_ready
import boto3
from kombu import Queue

logger = logging.getLogger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Configure boto3 to use LocalStack BEFORE celery loads
localstack_url = os.getenv('LOCALSTACK_URL', 'http://localhost:4566')

# Create a custom SQS client factory that forces LocalStack endpoint
def get_sqs_client():
    return boto3.client(
        'sqs',
        endpoint_url=localstack_url,
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        use_ssl=False
    )

# Set up environment to force LocalStack endpoint
os.environ['AWS_ENDPOINT_URL'] = localstack_url
os.environ['AWS_ENDPOINT_URL_SQS'] = localstack_url

app = Celery('algoitny')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Override broker transport options to ensure LocalStack is used
app.conf.broker_transport_options = {
    'region': 'us-east-1',
    'visibility_timeout': 3600,
    'polling_interval': 1,
    'queue_name_prefix': 'algoitny-',
    'is_secure': False,
    'endpoint_url': localstack_url,
    'sqs-base-url': localstack_url,
    # Force kombu to use our LocalStack endpoint
    'sqs_client_kwargs': {
        'endpoint_url': localstack_url,
        'region_name': 'us-east-1',
        'aws_access_key_id': 'test',
        'aws_secret_access_key': 'test',
        'use_ssl': False
    }
}

# Auto-discover tasks from all registered apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')


@worker_ready.connect
def recover_orphaned_jobs_on_startup(sender=None, **kwargs):
    """
    Recover orphaned jobs when worker starts - DynamoDB implementation.
    This is more reliable than shutdown handlers because shutdown may be abrupt.
    Marks jobs that have been stuck in PROCESSING state for > 10 minutes as FAILED.
    """
    logger.info("Worker starting up - checking for orphaned jobs...")

    try:
        from api.dynamodb.client import DynamoDBClient
        from api.dynamodb.repositories import (
            ProblemExtractionJobRepository,
            ScriptGenerationJobRepository,
            ProblemRepository
        )
        from datetime import datetime, timedelta, timezone as dt_timezone

        table = DynamoDBClient.get_table()
        extraction_repo = ProblemExtractionJobRepository(table)
        script_repo = ScriptGenerationJobRepository(table)
        problem_repo = ProblemRepository(table)

        # Consider jobs orphaned if they've been in PROCESSING for > 10 minutes
        cutoff_time = datetime.now(dt_timezone.utc) - timedelta(minutes=10)

        # Mark orphaned extraction jobs as FAILED
        extraction_jobs = extraction_repo.find_stale_jobs(cutoff_time)
        extraction_count = len(extraction_jobs)

        if extraction_count > 0:
            logger.warning(f"Found {extraction_count} orphaned extraction jobs (> 10 min in PROCESSING)")

            for job in extraction_jobs:
                job_id = job['job_id']
                platform = job['platform']
                problem_id = job['problem_id']

                # Update job status
                extraction_repo.update_job_status(
                    job_id=job_id,
                    status='FAILED',
                    error_message='Job orphaned - no updates for > 10 minutes'
                )

                # Update Problem metadata if problem exists
                problem = problem_repo.get_problem(platform=platform, problem_id=problem_id)
                if problem:
                    metadata = problem.get('metadata', {})
                    metadata['extraction_status'] = 'FAILED'
                    metadata['error_message'] = 'Job orphaned - no updates for > 10 minutes'
                    problem_repo.update_problem(
                        platform=platform,
                        problem_id=problem_id,
                        updates={'metadata': metadata}
                    )
                    logger.info(f"Marked orphaned extraction job {job_id} ({platform}/{problem_id}) as FAILED")
                else:
                    logger.warning(f"Problem {platform}/{problem_id} not found for job {job_id}")

        # Mark orphaned script generation jobs as FAILED
        script_jobs = script_repo.find_stale_jobs(cutoff_time)
        script_count = len(script_jobs)

        if script_count > 0:
            logger.warning(f"Found {script_count} orphaned script generation jobs (> 10 min in PROCESSING)")

            for job in script_jobs:
                job_id = job['job_id']
                script_repo.update_job_status(
                    job_id=job_id,
                    status='FAILED',
                    error_message='Job orphaned - no updates for > 10 minutes'
                )
                logger.info(f"Marked orphaned script job {job_id} as FAILED")

        total_recovered = extraction_count + script_count
        if total_recovered > 0:
            logger.warning(f"Recovered {total_recovered} orphaned jobs during startup")
        else:
            logger.info("No orphaned jobs found during startup")

    except Exception as e:
        logger.error(f"Error recovering orphaned jobs during startup: {e}", exc_info=True)
