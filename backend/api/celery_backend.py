"""Custom Celery result backend using Django ORM"""
import json
import logging
import django
from celery.backends.base import BaseBackend
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class DatabaseBackend(BaseBackend):
    """Custom Celery result backend that stores results in our TaskResult model"""

    def _get_task_model(self):
        """Import TaskResult model lazily to avoid Django app registry issues"""
        # Ensure Django is set up
        if not django.apps.apps.ready:
            django.setup()

        from api.models import TaskResult
        return TaskResult

    def _store_result(self, task_id, result, state, traceback=None, request=None, **kwargs):
        """Store task result in database"""
        TaskResult = self._get_task_model()

        # Prepare result data
        result_data = {
            'task_id': task_id,
            'status': state,
            'result': result if isinstance(result, dict) else {'data': result},
            'traceback': traceback,
        }

        # Update or create task result
        TaskResult.objects.update_or_create(
            task_id=task_id,
            defaults=result_data
        )
        logger.debug(f"Stored result for task {task_id}: {state}")
        return result

    def _get_task_meta_for(self, task_id):
        """Retrieve task result from database"""
        TaskResult = self._get_task_model()

        try:
            task_result = TaskResult.objects.get(task_id=task_id)
            return {
                'task_id': task_result.task_id,
                'status': task_result.status,
                'result': task_result.result,
                'traceback': task_result.traceback,
                'date_done': task_result.updated_at,
            }
        except ObjectDoesNotExist:
            return {'status': 'PENDING', 'result': None}

    def _forget(self, task_id):
        """Delete task result from database"""
        TaskResult = self._get_task_model()
        try:
            TaskResult.objects.filter(task_id=task_id).delete()
            logger.debug(f"Deleted task result {task_id}")
        except Exception as e:
            logger.error(f"Error deleting task result {task_id}: {e}")

    def cleanup(self):
        """Clean up old task results"""
        TaskResult = self._get_task_model()
        # Optionally implement cleanup logic
        pass
