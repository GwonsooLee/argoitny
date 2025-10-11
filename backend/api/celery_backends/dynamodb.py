"""
DynamoDB Celery Result Backend

This module provides a Celery result backend that stores task results
in DynamoDB. It supports both sync and async operations.

Task Result Storage Structure:
    PK: TASK#{task_id}
    SK: META
    tp: task_result
    dat: {
        status: str  # SUCCESS, FAILURE, PENDING, RETRY, REVOKED
        result: any  # Task result (JSON serializable)
        traceback: str  # Error traceback (if failed)
        children: list  # Child task IDs
    }
    exp: expire_timestamp  # Unix timestamp for TTL
    crt: created_timestamp
    upd: updated_timestamp
"""
import json
import logging
import time
from typing import Any, Dict, Optional
from celery.backends.base import BaseBackend
from celery import states
from kombu.utils.encoding import bytes_to_str, str_to_bytes

from django.conf import settings
from api.dynamodb.async_client import AsyncDynamoDBClient
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class DynamoDBBackend(BaseBackend):
    """
    DynamoDB result backend for Celery

    Features:
    - Stores task results in DynamoDB
    - Automatic TTL expiration
    - Compatible with both sync and async contexts
    - JSON serialization of results

    Configuration:
        CELERY_RESULT_BACKEND = 'api.celery_backends.dynamodb.DynamoDBBackend'
        CELERY_RESULT_EXPIRES = 86400  # 24 hours
        DJANGO_DYNAMODB_TABLE_NAME = 'algoitny_django'
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_name = getattr(settings, 'DJANGO_DYNAMODB_TABLE_NAME', 'algoitny_django')
        # Default expiration: 24 hours
        self.expires = kwargs.get('expires') or getattr(
            settings, 'CELERY_RESULT_EXPIRES', 86400
        )

    def _get_task_pk(self, task_id: str) -> str:
        """Generate partition key for task result"""
        return f'TASK#{task_id}'

    def _serialize_result(self, result: Any) -> str:
        """Serialize task result to JSON string"""
        try:
            return json.dumps(result)
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing result: {e}")
            return json.dumps(str(result))

    def _deserialize_result(self, data: str) -> Any:
        """Deserialize task result from JSON string"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    def _get_expiry_timestamp(self) -> int:
        """Get expiry timestamp for task result"""
        if self.expires:
            return int(time.time()) + int(self.expires)
        return 0

    async def _store_result_async(
        self,
        task_id: str,
        result: Any,
        state: str,
        traceback: Optional[str] = None,
        request: Optional[Dict] = None,
        **kwargs
    ) -> None:
        """
        Store task result in DynamoDB (async)

        Args:
            task_id: Task ID
            result: Task result
            state: Task state (SUCCESS, FAILURE, etc.)
            traceback: Error traceback (if failed)
            request: Task request metadata
        """
        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self.table_name)

                current_time = int(time.time())

                # Prepare result data
                result_data = {
                    'status': state,
                    'result': result,
                }

                if traceback:
                    result_data['traceback'] = traceback

                if request:
                    result_data['request'] = {
                        'id': request.get('id'),
                        'args': request.get('args'),
                        'kwargs': request.get('kwargs'),
                        'type': request.get('type'),
                    }

                # Get children tasks if any
                children = kwargs.get('children')
                if children:
                    result_data['children'] = children

                item = {
                    'PK': self._get_task_pk(task_id),
                    'SK': 'META',
                    'tp': 'task_result',
                    'dat': self._serialize_result(result_data),
                    'exp': self._get_expiry_timestamp(),
                    'crt': current_time,
                    'upd': current_time
                }

                await table.put_item(Item=item)

                logger.debug(f"Task result stored: {task_id}, state: {state}")

        except Exception as e:
            logger.error(f"Error storing task result {task_id}: {e}")
            raise

    async def _get_result_async(self, task_id: str) -> Optional[Dict]:
        """
        Get task result from DynamoDB (async)

        Args:
            task_id: Task ID

        Returns:
            Task result dictionary or None
        """
        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self.table_name)

                response = await table.get_item(
                    Key={
                        'PK': self._get_task_pk(task_id),
                        'SK': 'META'
                    }
                )

                item = response.get('Item')

                if not item:
                    return None

                # Check if expired
                expire_timestamp = item.get('exp', 0)
                if expire_timestamp and expire_timestamp < time.time():
                    # Result expired
                    await self._delete_result_async(task_id)
                    return None

                # Deserialize result data
                result_data_str = item.get('dat', '{}')
                return self._deserialize_result(result_data_str)

        except Exception as e:
            logger.error(f"Error getting task result {task_id}: {e}")
            return None

    async def _delete_result_async(self, task_id: str) -> None:
        """
        Delete task result from DynamoDB (async)

        Args:
            task_id: Task ID
        """
        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self.table_name)

                await table.delete_item(
                    Key={
                        'PK': self._get_task_pk(task_id),
                        'SK': 'META'
                    }
                )

                logger.debug(f"Task result deleted: {task_id}")

        except Exception as e:
            logger.error(f"Error deleting task result {task_id}: {e}")

    # Celery Backend Interface (sync methods)

    def _store_result(
        self,
        task_id: str,
        result: Any,
        state: str,
        traceback: Optional[str] = None,
        request: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """Store task result (sync wrapper)"""
        async_to_sync(self._store_result_async)(
            task_id, result, state, traceback, request, **kwargs
        )
        return result

    def _get_task_meta_for(self, task_id: str) -> Dict[str, Any]:
        """
        Get task metadata (sync wrapper)

        Returns:
            Task metadata dictionary with status and result
        """
        result_data = async_to_sync(self._get_result_async)(task_id)

        if not result_data:
            return {'status': states.PENDING, 'result': None}

        return {
            'status': result_data.get('status', states.PENDING),
            'result': result_data.get('result'),
            'traceback': result_data.get('traceback'),
            'children': result_data.get('children'),
            'task_id': task_id,
        }

    def _forget(self, task_id: str) -> None:
        """Delete task result (sync wrapper)"""
        async_to_sync(self._delete_result_async)(task_id)

    def cleanup(self) -> int:
        """
        Clean up expired results

        Note: With DynamoDB TTL enabled, this is handled automatically.
        This method is provided for compatibility.

        Returns:
            Number of results cleaned up
        """
        # TTL handles cleanup automatically
        logger.info("Cleanup handled by DynamoDB TTL")
        return 0

    def as_uri(self, include_password: bool = True) -> str:
        """Return the backend URI"""
        return f"dynamodb://{self.table_name}"
