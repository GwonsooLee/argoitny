"""Celery tasks for async processing"""
from celery import shared_task
from django.db import models
from .models import ScriptGenerationJob, Problem
from .services.gemini_service import GeminiService


@shared_task(bind=True, max_retries=3)
def generate_script_task(self, job_id):
    """
    Async task to generate test case generator script using Gemini AI

    Args:
        job_id: ID of the ScriptGenerationJob

    Returns:
        dict: Result with job_id and status
    """
    try:
        # Get the job
        job = ScriptGenerationJob.objects.get(id=job_id)

        # Update status to PROCESSING
        job.status = 'PROCESSING'
        job.celery_task_id = self.request.id
        job.save()

        # Prepare problem info for Gemini
        problem_info = {
            'platform': job.platform,
            'problem_id': job.problem_id,
            'title': job.title,
            'solution_code': job.solution_code or '',
            'language': job.language,
            'constraints': job.constraints,
            'tags': job.tags,
        }

        # Generate script using Gemini
        gemini_service = GeminiService()
        generator_code = gemini_service.generate_test_case_generator_code(problem_info)

        # Update job with result
        job.status = 'COMPLETED'
        job.generator_code = generator_code
        job.save()

        # Delete corresponding draft if exists (job completed successfully)
        try:
            draft = Problem.objects.filter(
                platform=job.platform,
                problem_id=job.problem_id
            ).annotate(
                test_case_count=models.Count('test_cases')
            ).filter(test_case_count=0).first()

            if draft:
                draft.delete()
        except Exception as e:
            # Log but don't fail the task if draft deletion fails
            print(f"Warning: Failed to delete draft: {str(e)}")

        return {
            'job_id': job_id,
            'status': 'COMPLETED',
            'message': 'Script generated successfully'
        }

    except ScriptGenerationJob.DoesNotExist:
        return {
            'job_id': job_id,
            'status': 'FAILED',
            'error': 'Job not found'
        }

    except Exception as e:
        # Update job with error
        try:
            job = ScriptGenerationJob.objects.get(id=job_id)
            job.status = 'FAILED'
            job.error_message = str(e)
            job.save()
        except:
            pass

        # Retry the task if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

        return {
            'job_id': job_id,
            'status': 'FAILED',
            'error': str(e)
        }
