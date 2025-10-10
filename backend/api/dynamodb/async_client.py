"""Async DynamoDB client for ASGI applications"""
import os
import logging
from typing import Optional
import aioboto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class AsyncDynamoDBClient:
    """
    Async DynamoDB client using aioboto3

    Usage:
        async with AsyncDynamoDBClient.get_session() as session:
            async with session.client('dynamodb') as client:
                response = await client.get_item(...)

    Or use context manager for table operations:
        async with AsyncDynamoDBClient.get_table() as table:
            response = await table.get_item(...)
    """
    _table_name = 'algoitny_main'
    _session = None

    @classmethod
    def get_session(cls):
        """
        Get aioboto3 session

        Returns:
            aioboto3.Session: Configured session for async AWS operations
        """
        if cls._session is None:
            cls._session = aioboto3.Session()
        return cls._session

    @classmethod
    def get_client_config(cls):
        """
        Get boto3 client configuration

        Returns:
            dict: Configuration for aioboto3 client
        """
        localstack_url = os.getenv('LOCALSTACK_URL')

        config = {
            'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            'config': Config(
                retries={'max_attempts': 3, 'mode': 'standard'},
                read_timeout=30,
                connect_timeout=10
            )
        }

        if localstack_url:
            # LocalStack configuration
            config.update({
                'endpoint_url': localstack_url,
                'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            })
            logger.debug(f"[Async DynamoDB] Using LocalStack at {localstack_url}")
        else:
            logger.debug("[Async DynamoDB] Using AWS")

        return config

    @classmethod
    def get_client(cls):
        """
        Get async DynamoDB client context manager

        Usage:
            async with AsyncDynamoDBClient.get_client() as client:
                response = await client.get_item(...)

        Returns:
            Async context manager for DynamoDB client
        """
        session = cls.get_session()
        config = cls.get_client_config()
        return session.client('dynamodb', **config)

    @classmethod
    def get_resource(cls):
        """
        Get async DynamoDB resource context manager

        Usage:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table('table_name')
                response = await table.get_item(...)

        Returns:
            Async context manager for DynamoDB resource
        """
        session = cls.get_session()
        config = cls.get_client_config()
        return session.resource('dynamodb', **config)

    @classmethod
    async def get_table(cls, table_name: Optional[str] = None):
        """
        Get async DynamoDB table

        Usage:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await AsyncDynamoDBClient.get_table(resource)
                response = await table.get_item(...)

        Args:
            table_name: Table name (defaults to cls._table_name)

        Returns:
            DynamoDB table resource
        """
        name = table_name or cls._table_name
        async with cls.get_resource() as resource:
            return await resource.Table(name)

    @classmethod
    def set_table_name(cls, table_name: str):
        """Set custom table name"""
        cls._table_name = table_name
