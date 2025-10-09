"""Script Generation Job Repository for DynamoDB"""
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from boto3.dynamodb.conditions import Key, Attr
from .base_repository import BaseRepository


class ScriptGenerationJobRepository(BaseRepository):
    """
    Repository for managing script generation jobs in DynamoDB

    Access Patterns:
    1. Get job by ID
    2. List all jobs (with filters: status, platform, problem_id)
    3. Create/Update/Delete job
    4. Query jobs by status
    5. Query jobs by platform + problem_id

    DynamoDB Structure:
        PK: 'SGJOB#{id}'              (e.g., 'SGJOB#1')
        SK: 'META'
        tp: 'sgjob'
        dat: {
            'plt': platform,
            'pid': problem_id,
            'tit': title,
            'url': problem_url,
            'tag': tags (list),
            'sol': solution_code,
            'lng': language,
            'con': constraints,
            'gen': generator_code,
            'sts': status (PENDING, PROCESSING, COMPLETED, FAILED),
            'tid': celery_task_id,
            'err': error_message
        }
        crt: created_timestamp
        upd: updated_timestamp
        GSI1PK: 'SGJOB#STATUS#{status}'     (for listing by status)
        GSI1SK: created_timestamp (Number)
    """

    def create_job(
        self,
        platform: str,
        problem_id: str,
        title: str,
        language: str,
        constraints: str,
        problem_url: str = '',
        tags: List[str] = None,
        solution_code: str = '',
        status: str = 'PENDING',
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new script generation job

        Args:
            platform: Platform name (baekjoon, codeforces, etc.)
            problem_id: Problem ID on the platform
            title: Problem title
            language: Programming language
            constraints: Problem constraints
            problem_url: URL to problem (optional)
            tags: Problem tags (optional)
            solution_code: Solution code (optional)
            status: Job status (default: PENDING)
            job_id: Optional job ID (if not provided, UUID will be generated)

        Returns:
            Created job item
        """
        timestamp = int(time.time())

        if tags is None:
            tags = []

        # Generate UUID-based ID if not provided
        if job_id is None:
            job_id = str(uuid.uuid4())

        item = {
            'PK': f'SGJOB#{job_id}',
            'SK': 'META',
            'tp': 'sgjob',
            'dat': {
                'plt': platform,
                'pid': problem_id,
                'tit': title,
                'url': problem_url,
                'tag': tags,
                'sol': solution_code,
                'lng': language,
                'con': constraints,
                'gen': '',  # generator_code initially empty
                'sts': status,
                'tid': '',  # celery_task_id initially empty
                'err': ''   # error_message initially empty
            },
            'crt': timestamp,
            'upd': timestamp,
            # GSI1 for status-based queries
            'GSI1PK': f'SGJOB#STATUS#{status}',
            'GSI1SK': f'{timestamp:020d}#{job_id}'  # Zero-padded timestamp for sorting + unique ID
        }

        self.table.put_item(Item=item)

        return self._transform_item(item, job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID

        Args:
            job_id: Job ID (UUID string)

        Returns:
            Job data or None if not found
        """
        pk = f'SGJOB#{job_id}'
        sk = 'META'

        response = self.table.get_item(Key={'PK': pk, 'SK': sk})
        item = response.get('Item')

        if not item:
            return None

        return self._transform_item(item, job_id)

    def update_job(
        self,
        job_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a job

        Args:
            job_id: Job ID
            updates: Dictionary of fields to update
                - status: Job status
                - celery_task_id: Celery task ID
                - generator_code: Generated code
                - error_message: Error message
                - solution_code: Solution code

        Returns:
            Updated job or None if not found
        """
        pk = f'SGJOB#{job_id}'
        sk = 'META'

        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}

        # Always update 'upd' timestamp
        timestamp = int(time.time())
        update_parts.append('#upd = :upd')
        expression_values[':upd'] = timestamp
        expression_names['#upd'] = 'upd'

        # Map updates to DynamoDB fields
        field_mapping = {
            'status': ('dat.sts', 'sts'),
            'celery_task_id': ('dat.tid', 'tid'),
            'generator_code': ('dat.gen', 'gen'),
            'error_message': ('dat.err', 'err'),
            'solution_code': ('dat.sol', 'sol'),
            'platform': ('dat.plt', 'plt'),
            'problem_id': ('dat.pid', 'pid'),
            'title': ('dat.tit', 'tit'),
            'problem_url': ('dat.url', 'url'),
            'tags': ('dat.tag', 'tag'),
            'language': ('dat.lng', 'lng'),
            'constraints': ('dat.con', 'con'),
        }

        for key, value in updates.items():
            if key in field_mapping:
                path, attr = field_mapping[key]
                update_parts.append(f'{path} = :{attr}')
                expression_values[f':{attr}'] = value

        # Update GSI1PK and GSI1SK if status is being updated
        if 'status' in updates:
            update_parts.append('GSI1PK = :gsi1pk, GSI1SK = :gsi1sk')
            expression_values[':gsi1pk'] = f'SGJOB#STATUS#{updates["status"]}'
            # Preserve timestamp and job_id in GSI1SK
            job_id_from_pk = self.get_job(job_id)
            if job_id_from_pk:
                created_at = int(job_id_from_pk.get('created_at', timestamp))
                expression_values[':gsi1sk'] = f'{created_at:020d}#{job_id}'

        if not update_parts:
            return self.get_job(job_id)

        update_expression = 'SET ' + ', '.join(update_parts)

        try:
            self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None
            )

            return self.get_job(job_id)
        except Exception:
            return None

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job

        Args:
            job_id: Job ID

        Returns:
            True if successful
        """
        pk = f'SGJOB#{job_id}'
        sk = 'META'

        try:
            self.table.delete_item(Key={'PK': pk, 'SK': sk})
            return True
        except Exception:
            return False

    def list_jobs(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        problem_id: Optional[str] = None,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict]]:
        """
        List jobs with optional filters

        Args:
            status: Filter by status (optional)
            platform: Filter by platform (optional)
            problem_id: Filter by problem_id (optional)
            limit: Maximum number of items to return
            last_evaluated_key: Pagination cursor

        Returns:
            Tuple of (list of jobs, next pagination cursor)
        """
        # If status filter provided, use GSI1
        if status:
            query_params = {
                'IndexName': 'GSI1',
                'KeyConditionExpression': Key('GSI1PK').eq(f'SGJOB#STATUS#{status}'),
                'Limit': limit,
                'ScanIndexForward': False  # Newest first
            }

            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.query(**query_params)
            items = response.get('Items', [])
        else:
            # Otherwise, scan with filter
            scan_params = {
                'FilterExpression': Attr('tp').eq('sgjob'),
                'Limit': limit
            }

            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.scan(**scan_params)
            items = response.get('Items', [])

        # Apply additional filters
        filtered_items = items
        if platform:
            filtered_items = [item for item in filtered_items if item.get('dat', {}).get('plt') == platform]
        if problem_id:
            filtered_items = [item for item in filtered_items if item.get('dat', {}).get('pid') == problem_id]

        # Transform items
        result = []
        for item in filtered_items:
            job_id = item['PK'].replace('SGJOB#', '')
            result.append(self._transform_item(item, job_id))

        # Sort by created_at descending
        result.sort(key=lambda x: x.get('created_at', 0), reverse=True)

        next_key = response.get('LastEvaluatedKey')
        return result, next_key

    def _transform_item(self, item: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Transform DynamoDB item to job format

        Args:
            item: DynamoDB item
            job_id: Job ID

        Returns:
            Job dictionary
        """
        dat = item.get('dat', {})

        return {
            'id': job_id,
            'platform': dat.get('plt', ''),
            'problem_id': dat.get('pid', ''),
            'title': dat.get('tit', ''),
            'problem_url': dat.get('url', ''),
            'tags': dat.get('tag', []),
            'solution_code': dat.get('sol', ''),
            'language': dat.get('lng', ''),
            'constraints': dat.get('con', ''),
            'generator_code': dat.get('gen', ''),
            'status': dat.get('sts', 'PENDING'),
            'celery_task_id': dat.get('tid', ''),
            'error_message': dat.get('err', ''),
            'created_at': item.get('crt', 0),
            'updated_at': item.get('upd', 0)
        }
