"""
Async DynamoDB session backend for Django

This module provides a fully async session backend that stores Django sessions
in DynamoDB using aioboto3. It's designed for ASGI applications using Daphne.

Session Storage Structure:
    PK: SESSION#{session_key}
    SK: META
    dat: {session_data}  # Serialized session data (JSON)
    exp: expire_timestamp  # Unix timestamp for TTL
    crt: created_timestamp
    upd: updated_timestamp
"""
import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core import signing
from django.utils import timezone

from api.dynamodb.async_client import AsyncDynamoDBClient
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class AsyncDynamoDBSessionStore(SessionBase):
    """
    Async DynamoDB session backend for Django

    Features:
    - Fully async using aioboto3
    - Automatic TTL expiration using DynamoDB TTL
    - Compatible with ASGI applications
    - No sync_to_async wrappers

    Usage:
        In settings.py:
        SESSION_ENGINE = 'api.sessions.dynamodb'
        SESSION_COOKIE_AGE = 3600  # 1 hour
    """

    def __init__(self, session_key=None):
        super().__init__(session_key)
        self._table_name = getattr(settings, 'DYNAMODB_SESSION_TABLE_NAME', 'algoitny_main')

    def _get_session_pk(self, session_key: str) -> str:
        """Generate partition key for session"""
        return f'SESSION#{session_key}'

    async def _get_table(self):
        """Get DynamoDB table resource"""
        async with AsyncDynamoDBClient.get_resource() as resource:
            return await resource.Table(self._table_name)

    def _serialize_session_data(self, session_dict: Dict[str, Any]) -> str:
        """Serialize session data to JSON string"""
        return json.dumps(session_dict)

    def _deserialize_session_data(self, data: str) -> Dict[str, Any]:
        """Deserialize session data from JSON string"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _get_expiry_timestamp(self) -> int:
        """Get expiry timestamp for session"""
        expiry_age = self.get_expiry_age()
        return int(time.time()) + expiry_age

    async def load(self) -> Dict[str, Any]:
        """
        Load session data from DynamoDB

        Returns:
            Session data dictionary
        """
        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self._table_name)

                response = await table.get_item(
                    Key={
                        'PK': self._get_session_pk(self.session_key),
                        'SK': 'META'
                    }
                )

                item = response.get('Item')

                if not item:
                    self._session_key = None
                    return {}

                # Check if expired
                expire_timestamp = item.get('exp', 0)
                if expire_timestamp and expire_timestamp < time.time():
                    # Session expired, delete it
                    await self.delete(self.session_key)
                    self._session_key = None
                    return {}

                # Deserialize session data
                session_data_str = item.get('dat', '{}')
                return self._deserialize_session_data(session_data_str)

        except Exception as e:
            logger.error(f"Error loading session {self.session_key}: {e}")
            return {}

    async def exists(self, session_key: str) -> bool:
        """
        Check if session exists in DynamoDB

        Args:
            session_key: Session key to check

        Returns:
            True if session exists and not expired, False otherwise
        """
        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self._table_name)

                response = await table.get_item(
                    Key={
                        'PK': self._get_session_pk(session_key),
                        'SK': 'META'
                    }
                )

                item = response.get('Item')

                if not item:
                    return False

                # Check if expired
                expire_timestamp = item.get('exp', 0)
                if expire_timestamp and expire_timestamp < time.time():
                    return False

                return True

        except Exception as e:
            logger.error(f"Error checking session existence {session_key}: {e}")
            return False

    def _generate_session_key(self) -> str:
        """Generate a new random session key"""
        # Same implementation as Django's SessionBase._get_new_session_key()
        # but without the exists() check
        import secrets
        return secrets.token_urlsafe(32)

    async def create(self) -> None:
        """
        Create a new session with a unique key

        Raises:
            CreateError: If unable to create a unique session key
        """
        # Try to create a new session with a unique key
        for i in range(10000):
            # Generate key without calling exists() (which is async)
            self._session_key = self._generate_session_key()
            try:
                # Try to save with must_create=True
                # This will fail if session already exists (collision detection)
                await self.save(must_create=True)
                self.modified = True
                return
            except CreateError:
                # Session key collision, try another one
                continue
            except Exception as e:
                # Handle ConditionalCheckFailedException as collision
                if 'ConditionalCheckFailedException' in str(e):
                    continue
                raise

        raise CreateError("Unable to create a new session key")

    async def save(self, must_create: bool = False) -> None:
        """
        Save session data to DynamoDB

        Args:
            must_create: If True, only create new session (don't update existing)

        Raises:
            CreateError: If must_create=True and session already exists
        """
        if self.session_key is None:
            return await self.create()

        # When must_create=True, we rely on DynamoDB's conditional check
        # instead of calling exists() which may not be awaited in some contexts

        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self._table_name)

                # Prepare session data
                session_data = self._get_session(no_load=must_create)
                serialized_data = self._serialize_session_data(session_data)

                # Calculate expiry
                expire_timestamp = self._get_expiry_timestamp()

                current_time = int(time.time())

                item = {
                    'PK': self._get_session_pk(self.session_key),
                    'SK': 'META',
                    'tp': 'session',
                    'dat': serialized_data,
                    'exp': expire_timestamp,
                    'upd': current_time
                }

                # Add created timestamp only for new sessions
                if must_create:
                    item['crt'] = current_time

                # Use put_item with condition for must_create
                if must_create:
                    await table.put_item(
                        Item=item,
                        ConditionExpression='attribute_not_exists(PK)'
                    )
                else:
                    await table.put_item(Item=item)

                logger.debug(f"Session saved: {self.session_key}, expires: {expire_timestamp}")

        except Exception as e:
            if must_create and 'ConditionalCheckFailedException' in str(e):
                raise CreateError("Session already exists")
            logger.error(f"Error saving session {self.session_key}: {e}")
            raise

    async def delete(self, session_key: Optional[str] = None) -> None:
        """
        Delete session from DynamoDB

        Args:
            session_key: Session key to delete (uses self.session_key if None)
        """
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key

        try:
            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(self._table_name)

                await table.delete_item(
                    Key={
                        'PK': self._get_session_pk(session_key),
                        'SK': 'META'
                    }
                )

                logger.debug(f"Session deleted: {session_key}")

        except Exception as e:
            logger.error(f"Error deleting session {session_key}: {e}")

    @classmethod
    async def clear_expired(cls) -> int:
        """
        Clear expired sessions

        Note: With DynamoDB TTL enabled, this is handled automatically.
        This method is provided for compatibility but may not be necessary.

        Returns:
            Number of sessions deleted
        """
        try:
            table_name = getattr(settings, 'DYNAMODB_SESSION_TABLE_NAME', 'algoitny_main')

            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(table_name)

                current_time = int(time.time())

                # Scan for expired sessions (this is expensive, use TTL instead)
                response = await table.scan(
                    FilterExpression='#tp = :tp AND #exp < :now',
                    ExpressionAttributeNames={
                        '#tp': 'tp',
                        '#exp': 'exp'
                    },
                    ExpressionAttributeValues={
                        ':tp': 'session',
                        ':now': current_time
                    }
                )

                items = response.get('Items', [])
                deleted_count = 0

                # Delete expired sessions in batch
                if items:
                    async with table.batch_writer() as batch:
                        for item in items:
                            await batch.delete_item(
                                Key={
                                    'PK': item['PK'],
                                    'SK': item['SK']
                                }
                            )
                            deleted_count += 1

                logger.info(f"Cleared {deleted_count} expired sessions")
                return deleted_count

        except Exception as e:
            logger.error(f"Error clearing expired sessions: {e}")
            return 0


# ============================================
# Sync Wrapper Methods for Django Compatibility
# ============================================
# Django's SessionMiddleware expects sync methods, so we provide
# sync wrappers that call the async methods using async_to_sync.
# This allows the session backend to work with both sync and async contexts.


class DynamoDBSessionStore(SessionBase):
    """
    Sync wrapper for AsyncDynamoDBSessionStore for Django middleware compatibility

    This class provides sync wrappers around the async methods, allowing
    the session backend to work with Django's standard SessionMiddleware.

    For async views, use AsyncDynamoDBSessionStore directly.
    For sync middleware compatibility, this class is used automatically by Django.

    Usage:
        In settings.py:
        SESSION_ENGINE = 'api.sessions.dynamodb'
    """

    def __init__(self, session_key=None):
        super().__init__(session_key)
        self._table_name = getattr(settings, 'DYNAMODB_SESSION_TABLE_NAME', 'algoitny_main')

    def _get_session_pk(self, session_key: str) -> str:
        """Generate partition key for session"""
        return f'SESSION#{session_key}'

    def _serialize_session_data(self, session_dict: Dict[str, Any]) -> str:
        """Serialize session data to JSON string"""
        return json.dumps(session_dict)

    def _deserialize_session_data(self, data: str) -> Dict[str, Any]:
        """Deserialize session data from JSON string"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _get_expiry_timestamp(self) -> int:
        """Get expiry timestamp for session"""
        expiry_age = self.get_expiry_age()
        return int(time.time()) + expiry_age

    async def _load_async(self) -> Dict[str, Any]:
        """Async load implementation"""
        store = AsyncDynamoDBSessionStore(self.session_key)
        return await store.load()

    async def _exists_async(self, session_key: str) -> bool:
        """Async exists implementation"""
        store = AsyncDynamoDBSessionStore(session_key)
        return await store.exists(session_key)

    async def _save_async(self, must_create: bool = False) -> None:
        """Async save implementation"""
        store = AsyncDynamoDBSessionStore(self.session_key)
        # Get session data using parent's _get_session method
        session_data = self._get_session(no_load=must_create)
        store._session_cache = session_data
        await store.save(must_create)

    async def _delete_async(self, session_key: Optional[str] = None) -> None:
        """Async delete implementation"""
        store = AsyncDynamoDBSessionStore(session_key or self.session_key)
        await store.delete(session_key)

    def load(self) -> Dict[str, Any]:
        """Sync wrapper for load()"""
        return async_to_sync(self._load_async)()

    def exists(self, session_key: str) -> bool:
        """Sync wrapper for exists()"""
        return async_to_sync(self._exists_async)(session_key)

    def _generate_session_key(self) -> str:
        """Generate a new random session key"""
        import secrets
        return secrets.token_urlsafe(32)

    def create(self) -> None:
        """
        Create a new session with a unique key

        Overrides parent to avoid async exists() calls
        """
        for i in range(10000):
            self._session_key = self._generate_session_key()
            try:
                self.save(must_create=True)
                self.modified = True
                return
            except CreateError:
                continue
            except Exception as e:
                if 'ConditionalCheckFailedException' in str(e):
                    continue
                raise
        raise CreateError("Unable to create a new session key")

    def save(self, must_create: bool = False) -> None:
        """Sync wrapper for save()"""
        if self.session_key is None:
            return self.create()
        return async_to_sync(self._save_async)(must_create)

    def delete(self, session_key: Optional[str] = None) -> None:
        """Sync wrapper for delete()"""
        async_to_sync(self._delete_async)(session_key)

    @classmethod
    def clear_expired(cls) -> int:
        """Sync wrapper for clear_expired()"""
        return async_to_sync(AsyncDynamoDBSessionStore.clear_expired)()
