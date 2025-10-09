"""DynamoDB client initialization"""
import os
import boto3
import logging
from botocore.config import Config

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Singleton DynamoDB client"""
    _client = None
    _resource = None
    _table_name = 'algoitny_main'
    _client_initialized = False
    _resource_initialized = False

    @classmethod
    def get_client(cls):
        """Get or create DynamoDB client"""
        if cls._client is None:
            # Check if running in LocalStack
            localstack_url = os.getenv('LOCALSTACK_URL')

            if localstack_url:
                # LocalStack configuration
                cls._client = boto3.client(
                    'dynamodb',
                    endpoint_url=localstack_url,
                    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                    config=Config(
                        retries={'max_attempts': 3, 'mode': 'standard'}
                    )
                )
                logger.info(f"[DynamoDB Init] Client initialized with LocalStack at {localstack_url}")
            else:
                # Production AWS configuration
                cls._client = boto3.client(
                    'dynamodb',
                    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                    config=Config(
                        retries={'max_attempts': 3, 'mode': 'standard'}
                    )
                )
                logger.info("[DynamoDB Init] Client initialized with AWS")

            cls._client_initialized = True

        return cls._client

    @classmethod
    def get_resource(cls):
        """Get or create DynamoDB resource (higher-level interface)"""
        if cls._resource is None:
            localstack_url = os.getenv('LOCALSTACK_URL')

            if localstack_url:
                cls._resource = boto3.resource(
                    'dynamodb',
                    endpoint_url=localstack_url,
                    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
                )
                logger.info(f"[DynamoDB Init] Resource initialized with LocalStack at {localstack_url}")
            else:
                cls._resource = boto3.resource(
                    'dynamodb',
                    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                )
                logger.info("[DynamoDB Init] Resource initialized with AWS")

            cls._resource_initialized = True

        return cls._resource

    @classmethod
    def get_table(cls):
        """Get DynamoDB table"""
        resource = cls.get_resource()
        return resource.Table(cls._table_name)

    @classmethod
    def set_table_name(cls, table_name):
        """Set custom table name"""
        cls._table_name = table_name
