"""Job Helper for pure DynamoDB storage (no PostgreSQL)"""
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    ScriptGenerationJobRepository,
    ProblemExtractionJobRepository
)
from datetime import datetime, timezone


class JobHelper:
    """Helper class for managing jobs with DynamoDB storage only"""

    @staticmethod
    def create_script_generation_job(**kwargs):
        """
        Create a ScriptGenerationJob in DynamoDB

        Args:
            platform, problem_id, title, language, constraints, problem_url, tags, solution_code, status

        Returns:
            Job dictionary from DynamoDB
        """
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)

        return job_repo.create_job(
            platform=kwargs.get('platform'),
            problem_id=kwargs.get('problem_id'),
            title=kwargs.get('title', ''),
            language=kwargs.get('language', 'python'),
            constraints=kwargs.get('constraints', ''),
            problem_url=kwargs.get('problem_url', ''),
            tags=kwargs.get('tags', []),
            solution_code=kwargs.get('solution_code', ''),
            status=kwargs.get('status', 'PENDING')
        )

    @staticmethod
    def create_problem_extraction_job(**kwargs):
        """
        Create a ProblemExtractionJob in DynamoDB

        Args:
            problem_url, platform, problem_id, problem_identifier, title, status

        Returns:
            Job dictionary from DynamoDB
        """
        table = DynamoDBClient.get_table()
        job_repo = ProblemExtractionJobRepository(table)

        return job_repo.create_job(
            problem_url=kwargs.get('problem_url'),
            platform=kwargs.get('platform', ''),
            problem_id=kwargs.get('problem_id', ''),
            problem_identifier=kwargs.get('problem_identifier', ''),
            title=kwargs.get('title', ''),
            status=kwargs.get('status', 'PENDING')
        )

    @staticmethod
    def get_script_generation_job(job_id):
        """Get ScriptGenerationJob from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)
        return job_repo.get_job(str(job_id))

    @staticmethod
    def get_problem_extraction_job(job_id):
        """Get ProblemExtractionJob from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ProblemExtractionJobRepository(table)
        return job_repo.get_job(str(job_id))

    @staticmethod
    def update_script_generation_job(job_id, updates):
        """Update ScriptGenerationJob in DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)
        return job_repo.update_job(str(job_id), updates)

    @staticmethod
    def update_problem_extraction_job(job_id, updates):
        """Update ProblemExtractionJob in DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ProblemExtractionJobRepository(table)
        return job_repo.update_job(str(job_id), updates)

    @staticmethod
    def conditional_update_script_job_to_processing(job_id, celery_task_id, expected_status='PENDING'):
        """
        Atomically update ScriptGenerationJob status to PROCESSING

        Args:
            job_id: Job ID
            celery_task_id: Celery task ID
            expected_status: Expected current status (default: PENDING)

        Returns:
            Tuple of (success: bool, job: Optional[Dict])
        """
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)
        return job_repo.conditional_update_status_to_processing(
            str(job_id),
            celery_task_id,
            expected_status
        )

    @staticmethod
    def list_script_generation_jobs(**kwargs):
        """List ScriptGenerationJobs from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)
        return job_repo.list_jobs(
            status=kwargs.get('status'),
            platform=kwargs.get('platform'),
            problem_id=kwargs.get('problem_id'),
            limit=kwargs.get('limit', 100)
        )

    @staticmethod
    def list_problem_extraction_jobs(**kwargs):
        """List ProblemExtractionJobs from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ProblemExtractionJobRepository(table)
        return job_repo.list_jobs(
            status=kwargs.get('status'),
            platform=kwargs.get('platform'),
            problem_id=kwargs.get('problem_id'),
            limit=kwargs.get('limit', 100)
        )

    @staticmethod
    def delete_script_generation_job(job_id):
        """Delete ScriptGenerationJob from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ScriptGenerationJobRepository(table)
        return job_repo.delete_job(str(job_id))

    @staticmethod
    def delete_problem_extraction_job(job_id):
        """Delete ProblemExtractionJob from DynamoDB"""
        table = DynamoDBClient.get_table()
        job_repo = ProblemExtractionJobRepository(table)
        return job_repo.delete_job(str(job_id))

    @staticmethod
    def format_job_for_serializer(job):
        """Format DynamoDB job for serializer/response"""
        if not job:
            return None

        from decimal import Decimal

        # Convert timestamps (handle Decimal type from DynamoDB)
        created_at = job.get('created_at', 0)
        updated_at = job.get('updated_at', 0)

        if isinstance(created_at, Decimal):
            created_at = float(created_at)
        if isinstance(updated_at, Decimal):
            updated_at = float(updated_at)

        if created_at:
            created_at = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
        if updated_at:
            updated_at = datetime.fromtimestamp(updated_at, tz=timezone.utc).isoformat()

        return {
            **job,
            'created_at': created_at,
            'updated_at': updated_at
        }
