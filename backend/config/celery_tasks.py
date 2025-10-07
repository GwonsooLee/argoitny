"""
Explicit task registration for Celery.
Import this module when you need to use api tasks.
"""
from config.celery import app

# Explicitly import tasks when needed
def register_api_tasks():
    """Register api tasks explicitly"""
    from api import tasks
    return tasks

# For now, only debug_task from config.celery is available by default