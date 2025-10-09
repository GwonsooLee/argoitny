"""UsageLog repository for DynamoDB operations - optimized for rate limiting"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from boto3.dynamodb.conditions import Key
from .base_repository import BaseRepository


class UsageLogRepository(BaseRepository):
    """
    Repository for UsageLog entity - CRITICAL HOT PATH for rate limiting

    Entity Pattern (optimized for rate limiting):
    - PK: USR#<user_id>#ULOG#<date_YYYYMMDD> (date-partitioned for efficient daily queries)
    - SK: ULOG#<timestamp>#<action>
    - tp: ulog
    - dat: {
        act: action (hint|execution),
        pid: problem_id (optional),
        met: metadata (optional)
    }
    - ttl: auto-delete after 90 days

    Performance:
    - check_rate_limit: 1-3ms latency, 0.5 RCU (COUNT query)
    - log_usage: 5-10ms latency, 1 WCU
    """

    TTL_DAYS = 90  # Auto-delete logs older than 90 days

    def __init__(self, table=None):
        """
        Initialize UsageLogRepository

        Args:
            table: DynamoDB table resource. If None, will be fetched from DynamoDBClient
        """
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

    def log_usage(
        self,
        user_id: int,
        action: str,
        problem_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log usage event (write operation) - LEGACY: uses user_id

        Args:
            user_id: User ID
            action: Action type ('hint' or 'execution')
            problem_id: Problem ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created usage log item

        Performance: 5-10ms latency, 1 WCU
        """
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        timestamp = int(now.timestamp())

        # Build usage log item
        item = {
            'PK': f'USR#{user_id}#ULOG#{date_str}',
            'SK': f'ULOG#{timestamp}#{action}',
            'tp': 'ulog',
            'dat': {
                'act': action,
            },
            'crt': timestamp,
            'ttl': timestamp + (self.TTL_DAYS * 86400)  # Auto-delete after 90 days
        }

        # Add optional fields
        if problem_id is not None:
            item['dat']['pid'] = problem_id

        if metadata:
            item['dat']['met'] = metadata

        # Write to DynamoDB
        self.put_item(item)

        return item

    def log_usage_by_email(
        self,
        email: str,
        action: str,
        platform: Optional[str] = None,
        problem_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log usage event by email (NEW: email-based)

        Args:
            email: User email
            action: Action type ('hint' or 'execution')
            platform: Platform name (optional, e.g. 'baekjoon')
            problem_number: Problem number (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created usage log item

        Performance: 5-10ms latency, 1 WCU
        """
        now = datetime.utcnow()
        date_str = now.strftime('%Y%m%d')
        timestamp = int(now.timestamp())

        # Build usage log item with email
        item = {
            'PK': f'EMAIL#{email}#ULOG#{date_str}',
            'SK': f'ULOG#{timestamp}#{action}',
            'tp': 'ulog',
            'dat': {
                'act': action,
            },
            'crt': timestamp,
            'ttl': timestamp + (self.TTL_DAYS * 86400)  # Auto-delete after 90 days
        }

        # Add optional fields
        if platform:
            item['dat']['plat'] = platform
        if problem_number:
            item['dat']['pnum'] = problem_number
        if metadata:
            item['dat']['met'] = metadata

        # Write to DynamoDB
        self.put_item(item)

        return item

    def get_daily_usage_count_by_email(
        self,
        email: str,
        action: str,
        date_str: Optional[str] = None
    ) -> int:
        """
        Get usage count by email for a specific day and action

        Args:
            email: User email
            action: Action type ('hint' or 'execution')
            date_str: Date string in YYYYMMDD format (defaults to today)

        Returns:
            Count of usage events

        Performance: 1-3ms latency, 0.5 RCU
        """
        # Default to today if not specified
        if date_str is None:
            date_str = datetime.utcnow().strftime('%Y%m%d')

        # Build partition key for date-specific query
        pk = f'EMAIL#{email}#ULOG#{date_str}'

        # Query with COUNT
        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('ULOG#'),
            FilterExpression=Key('dat').attr_exists() & Key('dat.act').eq(action),
            Select='COUNT'
        )

        return response.get('Count', 0)

    def get_daily_usage_count(
        self,
        user_id: int,
        action: str,
        date_str: Optional[str] = None
    ) -> int:
        """
        Get usage count for a specific day and action (CRITICAL HOT PATH)

        Uses COUNT query to avoid reading item data - extremely efficient.

        Args:
            user_id: User ID
            action: Action type ('hint' or 'execution')
            date_str: Date string in YYYYMMDD format (defaults to today)

        Returns:
            Count of usage events for the specified day and action

        Performance: 1-3ms latency, 0.5 RCU (COUNT query only)

        Example:
            >>> repo.get_daily_usage_count(12345, 'hint', '20251008')
            3
        """
        # Default to today if not specified
        if date_str is None:
            date_str = datetime.utcnow().strftime('%Y%m%d')

        # Build partition key for date-specific query
        pk = f'USR#{user_id}#ULOG#{date_str}'

        # Query with COUNT - no data transfer, just count
        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('ULOG#'),
            FilterExpression=Key('dat').attr_exists() & Key('dat.act').eq(action),
            Select='COUNT'  # Critical: only count, don't fetch data
        )

        return response.get('Count', 0)

    def get_usage_logs(
        self,
        user_id: int,
        date_str: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get usage logs for a specific day (admin/debugging)

        Args:
            user_id: User ID
            date_str: Date string in YYYYMMDD format (defaults to today)
            limit: Maximum number of logs to return

        Returns:
            List of usage log items (newest first)

        Performance: 10-20ms latency, 0.5 RCU × limit

        Example:
            >>> logs = repo.get_usage_logs(12345, '20251008', limit=50)
            >>> len(logs)
            50
        """
        # Default to today if not specified
        if date_str is None:
            date_str = datetime.utcnow().strftime('%Y%m%d')

        # Build partition key
        pk = f'USR#{user_id}#ULOG#{date_str}'

        # Query logs for the day
        items = self.query(
            key_condition_expression=Key('PK').eq(pk) & Key('SK').begins_with('ULOG#'),
            limit=limit,
            scan_index_forward=False  # Descending order (newest first)
        )

        return items

    def check_rate_limit(
        self,
        user_id: int,
        action: str,
        limit: int
    ) -> Tuple[bool, int, str]:
        """
        Check if user is within rate limit (MOST FREQUENT OPERATION)

        This is the hottest path in the entire application.
        Called on EVERY hint/execution request (~10,000+ req/min).

        Args:
            user_id: User ID
            action: Action type ('hint' or 'execution')
            limit: Maximum allowed actions per day (-1 = unlimited)

        Returns:
            Tuple of (is_allowed, current_count, reset_time_str)
            - is_allowed: True if within limit, False if exceeded
            - current_count: Current usage count for today
            - reset_time_str: ISO timestamp when limit resets (midnight UTC)

        Performance: 1-3ms latency, 0.5 RCU

        Example:
            >>> allowed, count, reset = repo.check_rate_limit(12345, 'hint', 5)
            >>> if not allowed:
            ...     raise RateLimitExceeded(f"Limit exceeded. Resets at {reset}")
        """
        # Unlimited plan
        if limit == -1:
            return True, 0, self._get_reset_time()

        # Get today's usage count
        current_count = self.get_daily_usage_count(user_id, action)

        # Check if within limit
        is_allowed = current_count < limit

        # Calculate reset time (midnight UTC next day)
        reset_time = self._get_reset_time()

        return is_allowed, current_count, reset_time

    def get_usage_summary(
        self,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage summary for the last N days (admin dashboard)

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Dictionary with usage statistics by action type

        Performance: ~50-100ms (queries multiple days)

        Example:
            >>> summary = repo.get_usage_summary(12345, days=7)
            >>> summary
            {
                'hint': {'total': 35, 'daily_avg': 5},
                'execution': {'total': 70, 'daily_avg': 10},
                'date_range': ['20251002', '20251008']
            }
        """
        # Generate date range
        date_range = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            date_range.append(date.strftime('%Y%m%d'))

        # Count by action type
        hint_count = 0
        execution_count = 0

        for date_str in date_range:
            hint_count += self.get_daily_usage_count(user_id, 'hint', date_str)
            execution_count += self.get_daily_usage_count(user_id, 'execution', date_str)

        return {
            'hint': {
                'total': hint_count,
                'daily_avg': round(hint_count / days, 2)
            },
            'execution': {
                'total': execution_count,
                'daily_avg': round(execution_count / days, 2)
            },
            'date_range': [date_range[-1], date_range[0]]  # [oldest, newest]
        }

    def delete_logs_before_date(self, user_id: int, date_str: str) -> int:
        """
        Delete all logs before a specific date for a user (admin/cleanup)

        Note: In production, TTL handles automatic deletion after 90 days.
        This method is for manual cleanup if needed.

        Args:
            user_id: User ID
            date_str: Date string in YYYYMMDD format

        Returns:
            Number of items deleted

        Performance: Slow (multiple queries + deletes), use sparingly
        """
        # Generate date range to check
        cutoff_date = datetime.strptime(date_str, '%Y%m%d')
        current_date = cutoff_date - timedelta(days=self.TTL_DAYS)
        deleted_count = 0

        while current_date < cutoff_date:
            date_key = current_date.strftime('%Y%m%d')
            pk = f'USR#{user_id}#ULOG#{date_key}'

            # Query all items for this day
            items = self.query(
                key_condition_expression=Key('PK').eq(pk) & Key('SK').begins_with('ULOG#')
            )

            # Delete each item
            for item in items:
                success = self.delete_item(item['PK'], item['SK'])
                if success:
                    deleted_count += 1

            current_date += timedelta(days=1)

        return deleted_count

    @staticmethod
    def _get_reset_time() -> str:
        """
        Get the reset time for rate limits (midnight UTC next day)

        Returns:
            ISO format timestamp string
        """
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.isoformat() + 'Z'

    @staticmethod
    def format_date(date: datetime) -> str:
        """
        Format datetime to YYYYMMDD string

        Args:
            date: datetime object

        Returns:
            Date string in YYYYMMDD format
        """
        return date.strftime('%Y%m%d')

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """
        Parse YYYYMMDD string to datetime

        Args:
            date_str: Date string in YYYYMMDD format

        Returns:
            datetime object
        """
        return datetime.strptime(date_str, '%Y%m%d')
