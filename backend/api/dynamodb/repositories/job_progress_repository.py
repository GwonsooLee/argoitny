"""Job Progress History Repository for DynamoDB"""
import time
from typing import List, Dict, Any, Optional, Tuple
from boto3.dynamodb.conditions import Key, Attr
from .base_repository import BaseRepository


class JobProgressHistoryRepository(BaseRepository):
    """
    Repository for managing job progress history in DynamoDB

    Access Patterns:
    1. Get all progress history for a job (by job_id + job_type)
    2. Add progress entry to a job
    3. Get latest progress for a job

    DynamoDB Structure:
        PK: 'JOB#{job_type}#{job_id}'  (e.g., 'JOB#extraction#123')
        SK: 'PROG#{timestamp}'         (e.g., 'PROG#1696752000')
        tp: 'prog'
        dat: {
            'stp': step (max 100 chars),
            'msg': message (full text),
            'sts': status ('started', 'in_progress', 'completed', 'failed')
        }
        crt: created_timestamp
    """

    def add_progress(
        self,
        job_type: str,
        job_id: int,
        step: str,
        message: str,
        status: str = 'in_progress'
    ) -> Dict[str, Any]:
        """
        Add a progress entry to a job

        Args:
            job_type: Type of job ('extraction' or 'generation')
            job_id: Job ID
            step: Step name (max 100 chars)
            message: Detailed progress message
            status: Progress status (started, in_progress, completed, failed)

        Returns:
            Created progress item
        """
        timestamp = int(time.time())

        # Validate job_type
        if job_type not in ['extraction', 'generation']:
            raise ValueError(f"Invalid job_type: {job_type}. Must be 'extraction' or 'generation'")

        # Validate status
        valid_statuses = ['started', 'in_progress', 'completed', 'failed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        # Truncate step to 100 chars
        step_truncated = step[:100]

        item = {
            'PK': f'JOB#{job_type}#{job_id}',
            'SK': f'PROG#{timestamp}',
            'tp': 'prog',
            'dat': {
                'stp': step_truncated,
                'msg': message,
                'sts': status
            },
            'crt': timestamp
        }

        self.table.put_item(Item=item)

        return {
            'job_type': job_type,
            'job_id': job_id,
            'step': step_truncated,
            'message': message,
            'status': status,
            'created_at': timestamp
        }

    def get_progress_history(
        self,
        job_type: str,
        job_id: int,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict]]:
        """
        Get progress history for a job with pagination support

        Args:
            job_type: Type of job ('extraction' or 'generation')
            job_id: Job ID
            limit: Maximum number of items to return
            last_evaluated_key: Pagination cursor from previous request

        Returns:
            Tuple of (list of progress entries, next page cursor)
            List of progress entries with structure:
            [
                {
                    'id': 'PROG#{timestamp}',
                    'step': 'Fetching webpage...',
                    'message': 'Fetching webpage...',
                    'status': 'completed',
                    'created_at': 1696752000
                },
                ...
            ]
            next page cursor is None if no more items
        """
        # Validate job_type
        if job_type not in ['extraction', 'generation']:
            raise ValueError(f"Invalid job_type: {job_type}. Must be 'extraction' or 'generation'")

        pk = f'JOB#{job_type}#{job_id}'

        # Query all progress entries for this job
        query_params = {
            'KeyConditionExpression': Key('PK').eq(pk) & Key('SK').begins_with('PROG#'),
            'ScanIndexForward': True,  # Oldest first
            'Limit': limit
        }

        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        response = self.table.query(**query_params)

        items = response.get('Items', [])
        next_key = response.get('LastEvaluatedKey')

        # Transform to response format
        result = []
        for item in items:
            dat = item.get('dat', {})

            result.append({
                'id': item['SK'],  # PROG#{timestamp}
                'step': dat.get('stp', ''),
                'message': dat.get('msg', ''),
                'status': dat.get('sts', 'in_progress'),
                'created_at': item.get('crt', 0)
            })

        return result, next_key

    def get_latest_progress(
        self,
        job_type: str,
        job_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent progress entry for a job

        Args:
            job_type: Type of job ('extraction' or 'generation')
            job_id: Job ID

        Returns:
            Latest progress entry or None if no progress exists
        """
        # Validate job_type
        if job_type not in ['extraction', 'generation']:
            raise ValueError(f"Invalid job_type: {job_type}. Must be 'extraction' or 'generation'")

        pk = f'JOB#{job_type}#{job_id}'

        # Query with descending order to get latest first
        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('PROG#'),
            ScanIndexForward=False,  # Newest first
            Limit=1
        )

        items = response.get('Items', [])

        if not items:
            return None

        item = items[0]
        dat = item.get('dat', {})

        return {
            'id': item['SK'],
            'step': dat.get('stp', ''),
            'message': dat.get('msg', ''),
            'status': dat.get('sts', 'in_progress'),
            'created_at': item.get('crt', 0)
        }

    def delete_progress_history(
        self,
        job_type: str,
        job_id: int
    ) -> bool:
        """
        Delete all progress history for a job using batch operations

        Args:
            job_type: Type of job ('extraction' or 'generation')
            job_id: Job ID

        Returns:
            True if successful
        """
        # Validate job_type
        if job_type not in ['extraction', 'generation']:
            raise ValueError(f"Invalid job_type: {job_type}. Must be 'extraction' or 'generation'")

        pk = f'JOB#{job_type}#{job_id}'

        # Get all progress entries
        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('PROG#')
        )

        items = response.get('Items', [])

        if not items:
            return True

        # Delete in batches of 25 (DynamoDB batch limit)
        for i in range(0, len(items), 25):
            batch = items[i:i+25]

            with self.table.batch_writer() as writer:
                for item in batch:
                    writer.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )

        return True
