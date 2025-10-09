"""
Custom Celery result backend - DISABLED

TaskResult model has been migrated to DynamoDB.
Celery result backend now uses Redis or disabled.

To re-enable with DynamoDB:
1. Create TaskResultRepository in api/dynamodb/repositories/
2. Update this backend to use DynamoDB instead of Django ORM

For now, use Redis backend or disable result backend in Celery config.
"""

# Custom backend disabled - use Redis or disable result backend
