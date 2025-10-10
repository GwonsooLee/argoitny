"""UserStats Repository for DynamoDB operations"""
import time
from typing import Dict, Optional
from decimal import Decimal
from .base_repository import BaseRepository


class UserStatsRepository(BaseRepository):
    """
    Repository for UserStats entity

    Entity Pattern:
    - PK: USER#{user_id}
    - SK: STATS
    - tp: stats
    - dat: {
        'uqp': {  # unique_problems map
            'baekjoon#1000': timestamp,
            'codeforces#1520E': timestamp
        },
        'tot': total_executions,
        'lut': last_updated_timestamp
    }
    - crt: created_timestamp
    - upd: updated_timestamp

    Example item:
    {
        'PK': 'USER#123',
        'SK': 'STATS',
        'tp': 'stats',
        'dat': {
            'uqp': {
                'baekjoon#1000': 1760106824998,
                'baekjoon#1001': 1760106824999,
                'codeforces#1520E': 1760106825000
            },
            'tot': 150,
            'lut': 1760106825000
        },
        'crt': 1760106824998,
        'upd': 1760106825000
    }
    """

    def __init__(self, table=None):
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

    def increment_execution(self, user_id: int, platform: str, problem_number: str):
        """
        Increment execution count and update unique problems

        Args:
            user_id: User ID
            platform: Platform name (e.g., 'baekjoon', 'codeforces')
            problem_number: Problem number/identifier

        Updates:
            - Adds/updates problem in unique_problems map with current timestamp
            - Increments total execution count
            - Updates last_updated timestamp
        """
        import logging
        logger = logging.getLogger(__name__)

        timestamp_ms = int(time.time() * 1000)
        problem_key = f'{platform}#{problem_number}'

        try:
            # Use atomic UpdateExpression to ensure thread-safety
            self.table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': 'STATS'
                },
                UpdateExpression='SET dat.uqp.#pk = :ts, dat.tot = if_not_exists(dat.tot, :zero) + :inc, dat.lut = :now, upd = :now',
                ExpressionAttributeNames={'#pk': problem_key},
                ExpressionAttributeValues={
                    ':ts': timestamp_ms,
                    ':inc': 1,
                    ':zero': 0,
                    ':now': timestamp_ms
                }
            )
            logger.info(f"[UserStats] Updated stats for user {user_id}: {problem_key}")
        except Exception as e:
            # If item doesn't exist, create it
            if 'ValidationException' in str(e) or 'ConditionalCheckFailedException' in str(e):
                logger.info(f"[UserStats] Creating initial stats for user {user_id}")
                self.create_stats(user_id, platform, problem_number)
            else:
                logger.error(f"[UserStats] Failed to update stats: {e}")
                raise

    def create_stats(self, user_id: int, platform: str, problem_number: str):
        """
        Create initial stats item

        Args:
            user_id: User ID
            platform: Platform name
            problem_number: Problem number/identifier
        """
        import logging
        logger = logging.getLogger(__name__)

        timestamp_ms = int(time.time() * 1000)
        problem_key = f'{platform}#{problem_number}'

        item = {
            'PK': f'USER#{user_id}',
            'SK': 'STATS',
            'tp': 'stats',
            'dat': {
                'uqp': {problem_key: timestamp_ms},
                'tot': 1,
                'lut': timestamp_ms
            },
            'crt': timestamp_ms,
            'upd': timestamp_ms
        }

        try:
            self.put_item(item)
            logger.info(f"[UserStats] Created stats for user {user_id} with problem {problem_key}")
        except Exception as e:
            logger.error(f"[UserStats] Failed to create stats: {e}")
            raise

    def get_stats(self, user_id: int) -> Optional[Dict]:
        """
        Get user statistics

        Args:
            user_id: User ID

        Returns:
            Stats item or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': 'STATS'
                }
            )
            return response.get('Item')
        except Exception:
            return None

    def count_unique_problems(self, user_id: int) -> int:
        """
        Fast count of unique problems (single read operation)

        Args:
            user_id: User ID

        Returns:
            Count of unique problems (0 if no stats exist)

        Performance:
            - Before: 125 RCU (scanning all history items)
            - After: 0.5 RCU (single GetItem)
        """
        item = self.get_stats(user_id)
        if not item:
            return 0

        return len(item.get('dat', {}).get('uqp', {}))

    def get_total_executions(self, user_id: int) -> int:
        """
        Get total execution count

        Args:
            user_id: User ID

        Returns:
            Total executions (0 if no stats exist)
        """
        item = self.get_stats(user_id)
        if not item:
            return 0

        tot = item.get('dat', {}).get('tot', 0)
        # Convert Decimal to int if needed
        if isinstance(tot, Decimal):
            return int(tot)
        return tot

    def get_last_updated(self, user_id: int) -> Optional[int]:
        """
        Get last updated timestamp

        Args:
            user_id: User ID

        Returns:
            Last updated timestamp in milliseconds or None
        """
        item = self.get_stats(user_id)
        if not item:
            return None

        lut = item.get('dat', {}).get('lut')
        # Convert Decimal to int if needed
        if isinstance(lut, Decimal):
            return int(lut)
        return lut
