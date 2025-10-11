"""Script Generation Job Repository for DynamoDB"""
import base64
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
        GSI2PK: 'SGJOB#{platform}#{problem_id}'  (for listing by platform+problem_id)
        GSI2SK: created_timestamp (Number)

    Note: solution_code is NOT stored in SGJOB - it should be fetched from Problem entity
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
            'GSI1SK': f'{timestamp:020d}#{job_id}',  # Zero-padded timestamp for sorting + unique ID
            # GSI2 for platform+problem_id queries
            'GSI2PK': f'SGJOB#{platform}#{problem_id}',
            'GSI2SK': f'{timestamp:020d}#{job_id}'
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
                # Base64 encode generator_code
                if key == 'generator_code' and value:
                    value = base64.b64encode(value.encode('utf-8')).decode('utf-8')
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

        # Update GSI2PK/GSI2SK if platform or problem_id is being updated
        if 'platform' in updates or 'problem_id' in updates:
            job_data = self.get_job(job_id)
            if job_data:
                new_platform = updates.get('platform', job_data.get('platform'))
                new_problem_id = updates.get('problem_id', job_data.get('problem_id'))
                created_at = int(job_data.get('created_at', timestamp))

                update_parts.append('GSI2PK = :gsi2pk, GSI2SK = :gsi2sk')
                expression_values[':gsi2pk'] = f'SGJOB#{new_platform}#{new_problem_id}'
                expression_values[':gsi2sk'] = f'{created_at:020d}#{job_id}'

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
        # Priority 1: If platform AND problem_id provided, use GSI2 (most efficient)
        if platform and problem_id:
            query_params = {
                'IndexName': 'GSI2',
                'KeyConditionExpression': Key('GSI2PK').eq(f'SGJOB#{platform}#{problem_id}'),
                'Limit': limit,
                'ScanIndexForward': False  # Newest first
            }

            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.query(**query_params)
            gsi_items = response.get('Items', [])

            # GSI2 has KEYS_ONLY projection, so fetch full items
            items = []
            for gsi_item in gsi_items:
                pk = gsi_item['PK']
                sk = gsi_item['SK']
                full_item_response = self.table.get_item(Key={'PK': pk, 'SK': sk})
                if 'Item' in full_item_response:
                    items.append(full_item_response['Item'])
        # Priority 2: If status filter provided, use GSI1
        elif status:
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
        # Priority 3: Otherwise, scan with filter
        else:
            scan_params = {
                'FilterExpression': Attr('tp').eq('sgjob'),
                'Limit': limit
            }

            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.scan(**scan_params)
            items = response.get('Items', [])

        # Apply additional filters (only needed if not using GSI2)
        filtered_items = items
        # Skip filtering if we already queried by platform+problem_id using GSI2
        if not (platform and problem_id):
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

    def find_stale_jobs(self, cutoff_time) -> List[Dict[str, Any]]:
        """
        Find jobs that have been in PROCESSING status before cutoff_time

        Args:
            cutoff_time: datetime object - jobs updated before this time are considered stale

        Returns:
            List of stale jobs
        """
        cutoff_timestamp = int(cutoff_time.timestamp())

        # Query jobs with PROCESSING status
        query_params = {
            'IndexName': 'GSI1',
            'KeyConditionExpression': Key('GSI1PK').eq('SGJOB#STATUS#PROCESSING'),
            'FilterExpression': Attr('upd').lt(cutoff_timestamp)
        }

        response = self.table.query(**query_params)
        items = response.get('Items', [])

        # Transform items
        result = []
        for item in items:
            job_id = item['PK'].replace('SGJOB#', '')
            result.append(self._transform_item(item, job_id))

        return result

    def conditional_update_status_to_processing(
        self,
        job_id: str,
        celery_task_id: str,
        expected_status: str = 'PENDING'
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Atomically update job status to PROCESSING only if it's currently in expected_status.
        This prevents duplicate execution by multiple workers.

        Args:
            job_id: Job ID
            celery_task_id: Celery task ID to set
            expected_status: Expected current status (default: PENDING)

        Returns:
            Tuple of (success: bool, job: Optional[Dict])
            - (True, job) if update succeeded
            - (False, None) if condition failed (already processing)
        """
        pk = f'SGJOB#{job_id}'
        sk = 'META'
        timestamp = int(time.time())

        try:
            # Get current job to preserve GSI1SK timestamp
            current_job = self.get_job(job_id)
            if not current_job:
                return (False, None)

            created_at = int(current_job.get('created_at', timestamp))

            # Conditional update: only update if status is expected_status
            self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression='SET dat.#sts = :new_status, dat.tid = :tid, #upd = :upd, GSI1PK = :gsi1pk, GSI1SK = :gsi1sk',
                ConditionExpression='dat.#sts = :expected_status',
                ExpressionAttributeNames={
                    '#sts': 'sts',
                    '#upd': 'upd'
                },
                ExpressionAttributeValues={
                    ':expected_status': expected_status,
                    ':new_status': 'PROCESSING',
                    ':tid': celery_task_id,
                    ':upd': timestamp,
                    ':gsi1pk': 'SGJOB#STATUS#PROCESSING',
                    ':gsi1sk': f'{created_at:020d}#{job_id}'
                }
            )

            # If we get here, update succeeded
            updated_job = self.get_job(job_id)
            return (True, updated_job)

        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            # Condition failed - job is not in expected status (likely already PROCESSING)
            return (False, None)
        except Exception as e:
            # Other error
            print(f"Error in conditional update: {e}")
            return (False, None)

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update job status and optionally error message

        Args:
            job_id: Job ID
            status: New status
            error_message: Optional error message

        Returns:
            Updated job or None if not found
        """
        updates = {'status': status}
        if error_message:
            updates['error_message'] = error_message

        return self.update_job(job_id, updates)

    def _transform_item(self, item: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Transform DynamoDB item to job format

        Args:
            item: DynamoDB item
            job_id: Job ID

        Returns:
            Job dictionary (solution_code should be fetched from Problem separately)
        """
        dat = item.get('dat', {})

        # Decode base64-encoded generator_code
        generator_code = dat.get('gen', '')
        if generator_code:
            try:
                generator_code = base64.b64decode(generator_code.encode('utf-8')).decode('utf-8')
            except Exception:
                # If decoding fails, use the original value (backward compatibility)
                pass

        return {
            'id': job_id,
            'job_id': job_id,  # Add job_id alias for compatibility
            'platform': dat.get('plt', ''),
            'problem_id': dat.get('pid', ''),
            'title': dat.get('tit', ''),
            'problem_url': dat.get('url', ''),
            'tags': dat.get('tag', []),
            'language': dat.get('lng', ''),
            'constraints': dat.get('con', ''),
            'generator_code': generator_code,
            'status': dat.get('sts', 'PENDING'),
            'celery_task_id': dat.get('tid', ''),
            'error_message': dat.get('err', ''),
            'created_at': item.get('crt', 0),
            'updated_at': item.get('upd', 0)
        }
