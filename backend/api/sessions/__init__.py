"""DynamoDB async session backend for Django"""
from .dynamodb import AsyncDynamoDBSessionStore, DynamoDBSessionStore

# Default export for Django SESSION_ENGINE setting
SessionStore = DynamoDBSessionStore

__all__ = ['AsyncDynamoDBSessionStore', 'DynamoDBSessionStore', 'SessionStore']
