"""Async repositories using aioboto3 directly"""
import time
from typing import Dict, List, Optional
from botocore.exceptions import ClientError


class AsyncSubscriptionPlanRepository:
    """True async SubscriptionPlan repository using aioboto3"""

    def __init__(self, table):
        """
        Initialize with aioboto3 table

        Args:
            table: aioboto3 DynamoDB table resource
        """
        self.table = table

    async def get_plan(self, plan_id: int) -> Optional[Dict]:
        """Get subscription plan by ID"""
        try:
            response = await self.table.get_item(
                Key={
                    'PK': f'PLAN#{plan_id}',
                    'SK': 'META'
                }
            )

            if 'Item' not in response:
                return None

            return self._transform_to_long_format(response['Item'])

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise

    async def list_plans(self, limit: int = 100) -> List[Dict]:
        """List all subscription plans"""
        try:
            # Scan for plans (small dataset, ~5 items)
            response = await self.table.scan(
                FilterExpression='#tp = :tp AND SK = :sk',
                ExpressionAttributeNames={
                    '#tp': 'tp'
                },
                ExpressionAttributeValues={
                    ':tp': 'plan',
                    ':sk': 'META'
                },
                Limit=limit
            )

            plans = []
            for item in response.get('Items', []):
                plans.append(self._transform_to_long_format(item))

            return plans

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return []
            raise

    async def create_plan(self, plan_data: Dict) -> Dict:
        """Create a new subscription plan"""
        plan_id = plan_data['id']
        timestamp = int(time.time())

        item = {
            'PK': f'PLAN#{plan_id}',
            'SK': 'META',
            'tp': 'plan',
            'dat': {
                'nm': plan_data['name'],
                'dsc': plan_data.get('description', ''),
                'mh': plan_data['max_hints_per_day'],
                'me': plan_data['max_executions_per_day'],
                'mp': plan_data.get('max_problems', -1),
                'cva': plan_data.get('can_view_all_problems', True),
                'crp': plan_data.get('can_register_problems', False),
                'prc': plan_data.get('price', 0),
                'act': plan_data.get('is_active', True),
            },
            'crt': timestamp,
            'upd': timestamp,
        }

        await self.table.put_item(Item=item)
        return self._transform_to_long_format(item)

    async def update_plan(self, plan_id: int, updates: Dict) -> Dict:
        """Update subscription plan"""
        field_mapping = {
            'name': 'nm',
            'description': 'dsc',
            'max_hints_per_day': 'mh',
            'max_executions_per_day': 'me',
            'max_problems': 'mp',
            'can_view_all_problems': 'cva',
            'can_register_problems': 'crp',
            'price': 'prc',
            'is_active': 'act',
        }

        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        for long_name, value in updates.items():
            if long_name in field_mapping:
                short_name = field_mapping[long_name]
                attr_name_dat = '#dat'
                attr_name_field = f'#dat_{short_name}'
                attr_value = f':val_{short_name}'

                update_expression_parts.append(f'{attr_name_dat}.{attr_name_field} = {attr_value}')
                expression_attribute_names[attr_name_dat] = 'dat'
                expression_attribute_names[attr_name_field] = short_name
                expression_attribute_values[attr_value] = value

        update_expression_parts.append('#upd = :upd')
        expression_attribute_names['#upd'] = 'upd'
        expression_attribute_values[':upd'] = int(time.time())

        update_expression = 'SET ' + ', '.join(update_expression_parts)

        response = await self.table.update_item(
            Key={
                'PK': f'PLAN#{plan_id}',
                'SK': 'META'
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )

        return self._transform_to_long_format(response['Attributes'])

    async def delete_plan(self, plan_id: int) -> bool:
        """Delete subscription plan"""
        try:
            await self.table.delete_item(
                Key={
                    'PK': f'PLAN#{plan_id}',
                    'SK': 'META'
                }
            )
            return True
        except ClientError:
            return False

    def _transform_to_long_format(self, item: Dict) -> Dict:
        """Transform DynamoDB item to long format"""
        dat = item.get('dat', {})
        plan_id = int(item['PK'].replace('PLAN#', ''))

        return {
            'id': plan_id,
            'name': dat.get('nm', ''),
            'description': dat.get('dsc', ''),
            'max_hints_per_day': dat.get('mh', 0),
            'max_executions_per_day': dat.get('me', 0),
            'max_problems': dat.get('mp', -1),
            'can_view_all_problems': dat.get('cva', True),
            'can_register_problems': dat.get('crp', False),
            'price': dat.get('prc', 0),
            'is_active': dat.get('act', True),
            'created_at': item.get('crt'),
            'updated_at': item.get('upd'),
        }


# Keep sync_to_async wrappers for other repositories that aren't causing issues
from asgiref.sync import sync_to_async
from .repositories import (
    ProblemRepository,
    UserRepository,
    SearchHistoryRepository,
    UsageLogRepository,
    ProblemExtractionJobRepository,
    ScriptGenerationJobRepository,
    JobProgressHistoryRepository
)


class AsyncProblemRepository:
    """Async wrapper for ProblemRepository"""

    def __init__(self, table=None):
        self._repo = ProblemRepository(table)

    async def get_problem(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_problem)(*args, **kwargs)

    async def get_problem_with_testcases(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_problem_with_testcases)(*args, **kwargs)

    async def list_completed_problems(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_completed_problems)(*args, **kwargs)

    async def list_draft_problems(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_draft_problems)(*args, **kwargs)

    async def create_problem(self, *args, **kwargs):
        return await sync_to_async(self._repo.create_problem)(*args, **kwargs)

    async def update_problem(self, *args, **kwargs):
        return await sync_to_async(self._repo.update_problem)(*args, **kwargs)

    async def delete_problem(self, *args, **kwargs):
        return await sync_to_async(self._repo.delete_problem)(*args, **kwargs)

    async def add_testcase(self, *args, **kwargs):
        return await sync_to_async(self._repo.add_testcase)(*args, **kwargs)

    async def get_testcases(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_testcases)(*args, **kwargs)


class AsyncUserRepository:
    """True async User repository using aioboto3"""

    def __init__(self, table):
        """
        Initialize with aioboto3 table

        Args:
            table: aioboto3 DynamoDB table resource
        """
        self.table = table

    async def list_active_users(self, limit: int = 1000) -> List[Dict]:
        """List all active users"""
        try:
            # Scan for active users
            response = await self.table.scan(
                FilterExpression='#tp = :tp AND #dat.#act = :act',
                ExpressionAttributeNames={
                    '#tp': 'tp',
                    '#dat': 'dat',
                    '#act': 'act'
                },
                ExpressionAttributeValues={
                    ':tp': 'usr',
                    ':act': True
                },
                Limit=limit
            )

            users = []
            for item in response.get('Items', []):
                # Extract user_id from PK (format: USR#{user_id})
                user_id = int(item['PK'].replace('USR#', ''))
                dat = item.get('dat', {})

                users.append({
                    'id': user_id,
                    'user_id': user_id,
                    'email': dat.get('em', ''),
                    'name': dat.get('nm', ''),
                    'is_active': dat.get('act', True),
                    'is_staff': dat.get('stf', False),
                    'subscription_plan_id': dat.get('plan'),
                    'created_at': item.get('crt'),
                    'updated_at': item.get('upd'),
                })

            return users

        except ClientError:
            return []

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email using GSI1"""
        try:
            response = await self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'EMAIL#{email}'
                },
                Limit=1
            )

            items = response.get('Items', [])
            if not items:
                return None

            item = items[0]
            user_id = int(item['PK'].replace('USR#', ''))
            dat = item.get('dat', {})

            return {
                'id': user_id,
                'user_id': user_id,
                'email': dat.get('em', ''),
                'name': dat.get('nm', ''),
                'picture': dat.get('pic', ''),
                'google_id': dat.get('gid', ''),
                'is_active': dat.get('act', True),
                'is_staff': dat.get('stf', False),
                'subscription_plan_id': dat.get('plan'),
                'created_at': item.get('crt'),
                'updated_at': item.get('upd'),
            }

        except ClientError:
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            response = await self.table.get_item(
                Key={
                    'PK': f'USR#{user_id}',
                    'SK': 'META'
                }
            )

            if 'Item' not in response:
                return None

            item = response['Item']
            dat = item.get('dat', {})

            return {
                'id': user_id,
                'user_id': user_id,
                'email': dat.get('em', ''),
                'name': dat.get('nm', ''),
                'picture': dat.get('pic', ''),
                'google_id': dat.get('gid', ''),
                'is_active': dat.get('act', True),
                'is_staff': dat.get('stf', False),
                'subscription_plan_id': dat.get('plan'),
                'created_at': item.get('crt'),
                'updated_at': item.get('upd'),
            }

        except ClientError:
            return None

    async def update_user(self, user_id: int, updates: Dict) -> bool:
        """Update user"""
        try:
            update_parts = []
            attr_names = {}
            attr_values = {}

            if 'subscription_plan_id' in updates:
                update_parts.append('#dat.#plan = :plan')
                attr_names['#dat'] = 'dat'
                attr_names['#plan'] = 'plan'
                attr_values[':plan'] = updates['subscription_plan_id']

            # Always update timestamp
            update_parts.append('#upd = :upd')
            attr_names['#upd'] = 'upd'
            attr_values[':upd'] = int(time.time())

            await self.table.update_item(
                Key={
                    'PK': f'USR#{user_id}',
                    'SK': 'META'
                },
                UpdateExpression='SET ' + ', '.join(update_parts),
                ExpressionAttributeNames=attr_names,
                ExpressionAttributeValues=attr_values
            )

            return True

        except ClientError:
            return False


class AsyncSearchHistoryRepository:
    """Async wrapper for SearchHistoryRepository"""

    def __init__(self, table=None):
        self._repo = SearchHistoryRepository(table)

    async def get_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_history)(*args, **kwargs)

    async def get_history_with_testcases(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_history_with_testcases)(*args, **kwargs)

    async def list_user_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_user_history)(*args, **kwargs)

    async def list_public_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_public_history)(*args, **kwargs)

    async def list_public_history_by_partition(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_public_history_by_partition)(*args, **kwargs)

    async def create_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.create_history)(*args, **kwargs)

    async def update_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.update_history)(*args, **kwargs)

    async def count_unique_problems(self, *args, **kwargs):
        return await sync_to_async(self._repo.count_unique_problems)(*args, **kwargs)


class AsyncUsageLogRepository:
    """Async wrapper for UsageLogRepository"""

    def __init__(self, table=None):
        self._repo = UsageLogRepository(table)

    async def create_usage_log(self, *args, **kwargs):
        return await sync_to_async(self._repo.create_usage_log)(*args, **kwargs)

    async def get_daily_usage_count_by_email(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_daily_usage_count_by_email)(*args, **kwargs)

    async def get_daily_usage_count(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_daily_usage_count)(*args, **kwargs)

    async def list_user_usage(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_user_usage)(*args, **kwargs)


class AsyncProblemExtractionJobRepository:
    """Async wrapper for ProblemExtractionJobRepository"""

    def __init__(self, table=None):
        self._repo = ProblemExtractionJobRepository(table)

    async def get_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_job)(*args, **kwargs)

    async def create_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.create_job)(*args, **kwargs)

    async def update_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.update_job)(*args, **kwargs)

    async def list_jobs(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_jobs)(*args, **kwargs)

    async def delete_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.delete_job)(*args, **kwargs)


class AsyncScriptGenerationJobRepository:
    """Async wrapper for ScriptGenerationJobRepository"""

    def __init__(self, table=None):
        self._repo = ScriptGenerationJobRepository(table)

    async def get_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_job)(*args, **kwargs)

    async def create_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.create_job)(*args, **kwargs)

    async def update_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.update_job)(*args, **kwargs)

    async def list_jobs(self, *args, **kwargs):
        return await sync_to_async(self._repo.list_jobs)(*args, **kwargs)

    async def delete_job(self, *args, **kwargs):
        return await sync_to_async(self._repo.delete_job)(*args, **kwargs)


class AsyncJobProgressHistoryRepository:
    """Async wrapper for JobProgressHistoryRepository"""

    def __init__(self, table=None):
        self._repo = JobProgressHistoryRepository(table)

    async def add_progress(self, *args, **kwargs):
        return await sync_to_async(self._repo.add_progress)(*args, **kwargs)

    async def get_progress_history(self, *args, **kwargs):
        return await sync_to_async(self._repo.get_progress_history)(*args, **kwargs)
