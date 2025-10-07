"""Minimal Celery configuration without api tasks"""
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('algoitny-minimal')

# Manually configure Celery without loading Django settings
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='django-db',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@app.task(bind=True, ignore_result=False)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Debug task executing! Request: {self.request!r}')
    return f'Debug task executed successfully! Request ID: {self.request.id}'