"""DynamoDB Celery result backend"""
from .dynamodb import DynamoDBBackend

__all__ = ['DynamoDBBackend']
