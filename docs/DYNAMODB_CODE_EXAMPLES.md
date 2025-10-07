# DynamoDB Implementation Code Examples

This document provides practical Python code examples for implementing the DynamoDB schema design.

## Table of Contents
1. [Table Creation](#table-creation)
2. [Repository Pattern](#repository-pattern)
3. [Common Operations](#common-operations)
4. [Migration Scripts](#migration-scripts)
5. [Testing Examples](#testing-examples)

---

## Table Creation

### Create AlgoItny-Main Table

```python
import boto3

def create_main_table():
    """Create the main table with GSIs"""
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    table_name = 'AlgoItny-Main'

    try:
        response = dynamodb.create_table(
            TableName=table_name,
            # Primary key
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},   # Partition key
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}    # Sort key
            ],
            # Attribute definitions (only for keys)
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI3SK', 'AttributeType': 'S'},
            ],
            # Provisioned capacity
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 25,
                'WriteCapacityUnits': 10
            },
            # Global Secondary Indexes
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 25,
                        'WriteCapacityUnits': 10
                    }
                },
                {
                    'IndexName': 'GSI2',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 25,
                        'WriteCapacityUnits': 10
                    }
                },
                {
                    'IndexName': 'GSI3',
                    'KeySchema': [
                        {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 25,
                        'WriteCapacityUnits': 10
                    }
                }
            ],
            # Enable TTL
            Tags=[
                {'Key': 'Environment', 'Value': 'production'},
                {'Key': 'Application', 'Value': 'AlgoItny'}
            ]
        )

        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        # Enable TTL
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'TTL'
            }
        )

        # Enable Point-in-Time Recovery
        dynamodb.update_continuous_backups(
            TableName=table_name,
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            }
        )

        print(f"Table {table_name} created successfully")
        return response

    except dynamodb.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists")


def create_users_table():
    """Create the Users table"""
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    table_name = 'AlgoItny-Users'

    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI3SK', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',  # On-demand
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'GSI2',
                'KeySchema': [
                    {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'GSI3',
                'KeySchema': [
                    {'AttributeName': 'GSI3PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI3SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )

    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    print(f"Table {table_name} created successfully")


def create_plans_table():
    """Create the Plans table"""
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')

    table_name = 'AlgoItny-Plans'

    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )

    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    print(f"Table {table_name} created successfully")


if __name__ == '__main__':
    create_main_table()
    create_users_table()
    create_plans_table()
```

---

## Repository Pattern

### Base Repository

```python
# repositories/base.py
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
import uuid
from typing import Dict, List, Optional, Any


class DynamoDBRepository:
    """Base repository for DynamoDB operations"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.client = boto3.client('dynamodb')

    def get_item(self, pk: str, sk: str) -> Optional[Dict]:
        """Get a single item by primary key"""
        response = self.table.get_item(Key={'PK': pk, 'SK': sk})
        return response.get('Item')

    def put_item(self, item: Dict) -> Dict:
        """Put an item into the table"""
        response = self.table.put_item(Item=item)
        return item

    def update_item(self, pk: str, sk: str, updates: Dict) -> Dict:
        """Update specific attributes of an item"""
        update_expression = "SET " + ", ".join([f"#{k} = :{k}" for k in updates.keys()])
        expression_attribute_names = {f"#{k}": k for k in updates.keys()}
        expression_attribute_values = {f":{k}": v for k, v in updates.items()}

        response = self.table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        return response.get('Attributes', {})

    def delete_item(self, pk: str, sk: str) -> None:
        """Delete an item"""
        self.table.delete_item(Key={'PK': pk, 'SK': sk})

    def query(
        self,
        key_condition: str,
        expression_values: Dict,
        index_name: Optional[str] = None,
        filter_expression: Optional[str] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
        exclusive_start_key: Optional[Dict] = None
    ) -> Dict:
        """Query items with flexible parameters"""
        params = {
            'KeyConditionExpression': key_condition,
            'ExpressionAttributeValues': expression_values,
            'ScanIndexForward': scan_forward
        }

        if index_name:
            params['IndexName'] = index_name
        if filter_expression:
            params['FilterExpression'] = filter_expression
        if limit:
            params['Limit'] = limit
        if exclusive_start_key:
            params['ExclusiveStartKey'] = exclusive_start_key

        return self.table.query(**params)

    def batch_write(self, items: List[Dict]) -> None:
        """Batch write items (up to 25 at a time)"""
        with self.table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)

    @staticmethod
    def now_iso() -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + 'Z'

    @staticmethod
    def generate_uuid() -> str:
        """Generate a UUID"""
        return str(uuid.uuid4())
```

### Problem Repository

```python
# repositories/problem_repository.py
from typing import List, Optional, Dict
from .base import DynamoDBRepository
from boto3.dynamodb.conditions import Key


class ProblemRepository(DynamoDBRepository):
    """Repository for Problem and TestCase entities"""

    def __init__(self):
        super().__init__('AlgoItny-Main')

    def create_problem(
        self,
        platform: str,
        problem_id: str,
        title: str,
        language: str,
        solution_code: str = '',
        problem_url: str = '',
        tags: List[str] = None,
        constraints: str = '',
        is_completed: bool = False
    ) -> Dict:
        """Create a new problem"""
        timestamp = self.now_iso()
        internal_id = self.generate_uuid()

        item = {
            'PK': f'PROBLEM#{platform}#{problem_id}',
            'SK': 'METADATA',
            'EntityType': 'Problem',
            'InternalId': internal_id,
            'Platform': platform,
            'ProblemId': problem_id,
            'Title': title,
            'ProblemUrl': problem_url,
            'Tags': tags or [],
            'SolutionCode': solution_code,
            'Language': language,
            'Constraints': constraints,
            'IsCompleted': is_completed,
            'IsDeleted': False,
            'Metadata': {},
            'CreatedAt': timestamp,
            'UpdatedAt': timestamp,
            'GSI1PK': f'PLATFORM#{platform}',
            'GSI1SK': timestamp,
            'GSI2PK': f'COMPLETED#{str(is_completed).lower()}',
            'GSI2SK': timestamp,
            'GSI3PK': f'LANGUAGE#{language}',
            'GSI3SK': timestamp,
        }

        return self.put_item(item)

    def get_problem(self, platform: str, problem_id: str) -> Optional[Dict]:
        """Get a problem by platform and problem_id"""
        pk = f'PROBLEM#{platform}#{problem_id}'
        return self.get_item(pk, 'METADATA')

    def get_problem_with_test_cases(self, platform: str, problem_id: str) -> Dict:
        """Get problem with all its test cases"""
        pk = f'PROBLEM#{platform}#{problem_id}'

        response = self.table.query(
            KeyConditionExpression=Key('PK').eq(pk)
        )

        items = response['Items']

        problem = next((item for item in items if item['SK'] == 'METADATA'), None)
        test_cases = [
            item for item in items
            if item['SK'].startswith('TESTCASE#')
        ]

        # Sort test cases by timestamp
        test_cases.sort(key=lambda x: x['SK'])

        return {
            'problem': problem,
            'test_cases': test_cases
        }

    def create_test_cases(
        self,
        platform: str,
        problem_id: str,
        test_cases: List[Dict]
    ) -> None:
        """Create multiple test cases for a problem"""
        pk = f'PROBLEM#{platform}#{problem_id}'
        timestamp = self.now_iso()

        items = []
        for tc in test_cases:
            tc_id = self.generate_uuid()
            item = {
                'PK': pk,
                'SK': f'TESTCASE#{timestamp}#{tc_id}',
                'EntityType': 'TestCase',
                'TestCaseId': tc_id,
                'Input': tc['input'],
                'Output': tc['output'],
                'CreatedAt': timestamp
            }
            items.append(item)

        self.batch_write(items)

    def list_problems_by_platform(
        self,
        platform: str,
        limit: int = 20,
        last_key: Optional[Dict] = None
    ) -> Dict:
        """List problems by platform, ordered by creation time"""
        response = self.query(
            key_condition='GSI1PK = :pk',
            expression_values={':pk': f'PLATFORM#{platform}'},
            index_name='GSI1',
            limit=limit,
            scan_forward=False,  # Descending order
            exclusive_start_key=last_key
        )

        return {
            'items': response['Items'],
            'last_key': response.get('LastEvaluatedKey'),
            'has_more': 'LastEvaluatedKey' in response
        }

    def list_completed_problems(
        self,
        limit: int = 20,
        last_key: Optional[Dict] = None
    ) -> Dict:
        """List completed problems"""
        response = self.query(
            key_condition='GSI2PK = :pk',
            expression_values={':pk': 'COMPLETED#true'},
            index_name='GSI2',
            limit=limit,
            scan_forward=False,
            exclusive_start_key=last_key
        )

        return {
            'items': response['Items'],
            'last_key': response.get('LastEvaluatedKey'),
            'has_more': 'LastEvaluatedKey' in response
        }

    def list_problems_by_language(
        self,
        language: str,
        limit: int = 20,
        last_key: Optional[Dict] = None
    ) -> Dict:
        """List problems by programming language"""
        response = self.query(
            key_condition='GSI3PK = :pk',
            expression_values={':pk': f'LANGUAGE#{language}'},
            index_name='GSI3',
            limit=limit,
            scan_forward=False,
            exclusive_start_key=last_key
        )

        return {
            'items': response['Items'],
            'last_key': response.get('LastEvaluatedKey'),
            'has_more': 'LastEvaluatedKey' in response
        }

    def update_problem_completion(
        self,
        platform: str,
        problem_id: str,
        is_completed: bool
    ) -> Dict:
        """Update problem completion status"""
        pk = f'PROBLEM#{platform}#{problem_id}'
        timestamp = self.now_iso()

        return self.update_item(
            pk=pk,
            sk='METADATA',
            updates={
                'IsCompleted': is_completed,
                'UpdatedAt': timestamp,
                'GSI2PK': f'COMPLETED#{str(is_completed).lower()}',
                'GSI2SK': timestamp
            }
        )

    def soft_delete_problem(
        self,
        platform: str,
        problem_id: str,
        reason: str = ''
    ) -> Dict:
        """Soft delete a problem (remove from indexes)"""
        pk = f'PROBLEM#{platform}#{problem_id}'
        timestamp = self.now_iso()

        # Remove GSI attributes to remove from indexes (sparse index pattern)
        response = self.table.update_item(
            Key={'PK': pk, 'SK': 'METADATA'},
            UpdateExpression='''
                SET IsDeleted = :deleted,
                    DeletedAt = :time,
                    DeletedReason = :reason,
                    UpdatedAt = :time
                REMOVE GSI1PK, GSI1SK, GSI2PK, GSI2SK, GSI3PK, GSI3SK
            ''',
            ExpressionAttributeValues={
                ':deleted': True,
                ':time': timestamp,
                ':reason': reason
            },
            ReturnValues='ALL_NEW'
        )

        return response.get('Attributes', {})
```

### Search History Repository

```python
# repositories/search_history_repository.py
from typing import List, Optional, Dict
from .base import DynamoDBRepository
from boto3.dynamodb.conditions import Key


class SearchHistoryRepository(DynamoDBRepository):
    """Repository for SearchHistory entities"""

    def __init__(self):
        super().__init__('AlgoItny-Main')

    def create_search_history(
        self,
        user_id: str,
        user_identifier: str,
        problem_pk: str,
        problem_id: str,
        platform: str,
        problem_number: str,
        problem_title: str,
        language: str,
        code: str,
        result_summary: Dict,
        passed_count: int,
        failed_count: int,
        total_count: int,
        is_code_public: bool = False,
        test_results: List[Dict] = None,
        metadata: Dict = None
    ) -> Dict:
        """Create a new search history entry"""
        timestamp = self.now_iso()
        history_id = self.generate_uuid()

        item = {
            'PK': f'USER#{user_id}',
            'SK': f'HISTORY#{timestamp}#{history_id}',
            'EntityType': 'SearchHistory',
            'HistoryId': history_id,
            'UserId': user_id,
            'UserIdentifier': user_identifier,
            'ProblemPK': problem_pk,
            'ProblemId': problem_id,
            'Platform': platform,
            'ProblemNumber': problem_number,
            'ProblemTitle': problem_title,
            'Language': language,
            'Code': code,
            'ResultSummary': result_summary,
            'PassedCount': passed_count,
            'FailedCount': failed_count,
            'TotalCount': total_count,
            'IsCodePublic': is_code_public,
            'TestResults': test_results or [],
            'Hints': None,
            'Metadata': metadata or {},
            'CreatedAt': timestamp,
            'GSI2PK': f'PLATFORM#{platform}',
            'GSI2SK': timestamp,
            'GSI3PK': f'LANGUAGE#{language}',
            'GSI3SK': timestamp,
        }

        # Only add GSI1 if public (sparse index)
        if is_code_public:
            item['GSI1PK'] = 'PUBLIC#true'
            item['GSI1SK'] = timestamp

        return self.put_item(item)

    def get_user_history(
        self,
        user_id: str,
        limit: int = 20,
        last_key: Optional[Dict] = None
    ) -> Dict:
        """Get user's search history"""
        response = self.query(
            key_condition='PK = :pk AND begins_with(SK, :sk)',
            expression_values={
                ':pk': f'USER#{user_id}',
                ':sk': 'HISTORY#'
            },
            limit=limit,
            scan_forward=False,
            exclusive_start_key=last_key
        )

        return {
            'items': response['Items'],
            'last_key': response.get('LastEvaluatedKey'),
            'has_more': 'LastEvaluatedKey' in response
        }

    def get_public_history(
        self,
        limit: int = 20,
        last_key: Optional[Dict] = None
    ) -> Dict:
        """Get public search history feed"""
        response = self.query(
            key_condition='GSI1PK = :pk',
            expression_values={':pk': 'PUBLIC#true'},
            index_name='GSI1',
            limit=limit,
            scan_forward=False,
            exclusive_start_key=last_key
        )

        return {
            'items': response['Items'],
            'last_key': response.get('LastEvaluatedKey'),
            'has_more': 'LastEvaluatedKey' in response
        }

    def update_hints(
        self,
        user_id: str,
        history_id: str,
        hints: List[str]
    ) -> Dict:
        """Update hints for a search history entry"""
        # Need to find the item first to get the full SK
        response = self.query(
            key_condition='PK = :pk AND begins_with(SK, :sk)',
            expression_values={
                ':pk': f'USER#{user_id}',
                ':sk': 'HISTORY#'
            },
            filter_expression='HistoryId = :hid',
        )

        if not response['Items']:
            raise ValueError(f"History {history_id} not found")

        item = response['Items'][0]
        sk = item['SK']

        return self.update_item(
            pk=f'USER#{user_id}',
            sk=sk,
            updates={'Hints': hints}
        )
```

### Usage Log Repository

```python
# repositories/usage_log_repository.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from .base import DynamoDBRepository


class UsageLogRepository(DynamoDBRepository):
    """Repository for UsageLog entities"""

    def __init__(self):
        super().__init__('AlgoItny-Main')

    def log_usage(
        self,
        user_id: str,
        action: str,  # 'hint' or 'execution'
        problem_id: Optional[str] = None,
        problem_pk: Optional[str] = None,
        metadata: Dict = None
    ) -> Dict:
        """Log a usage action"""
        timestamp = self.now_iso()
        log_id = self.generate_uuid()
        date = datetime.utcnow().strftime('%Y-%m-%d')

        # Calculate TTL (90 days from now)
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())

        item = {
            'PK': f'USER#{user_id}',
            'SK': f'USAGE#{date}#{action}#{timestamp}#{log_id}',
            'EntityType': 'UsageLog',
            'LogId': log_id,
            'UserId': user_id,
            'Action': action,
            'ProblemId': problem_id,
            'ProblemPK': problem_pk,
            'Metadata': metadata or {},
            'CreatedAt': timestamp,
            'TTL': ttl  # Auto-delete after 90 days
        }

        return self.put_item(item)

    def count_today_usage(
        self,
        user_id: str,
        action: str
    ) -> int:
        """Count usage for today"""
        today = datetime.utcnow().strftime('%Y-%m-%d')

        response = self.query(
            key_condition='PK = :pk AND begins_with(SK, :sk)',
            expression_values={
                ':pk': f'USER#{user_id}',
                ':sk': f'USAGE#{today}#{action}#'
            },
            select='COUNT'  # Only count, don't retrieve items
        )

        return response['Count']

    def get_usage_logs(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        action: Optional[str] = None
    ) -> list:
        """Get usage logs for a date range"""
        sk_prefix = f'USAGE#{start_date}'
        sk_end = f'USAGE#{end_date}#\uffff'

        if action:
            sk_prefix = f'USAGE#{start_date}#{action}#'
            sk_end = f'USAGE#{end_date}#{action}#\uffff'

        response = self.table.query(
            KeyConditionExpression='PK = :pk AND SK BETWEEN :start AND :end',
            ExpressionAttributeValues={
                ':pk': f'USER#{user_id}',
                ':start': sk_prefix,
                ':end': sk_end
            }
        )

        return response['Items']
```

---

## Common Operations

### Rate Limiting Check

```python
# services/rate_limiter.py
from repositories.usage_log_repository import UsageLogRepository
from repositories.user_repository import UserRepository


class RateLimiter:
    """Rate limiting service using DynamoDB"""

    def __init__(self):
        self.usage_repo = UsageLogRepository()
        self.user_repo = UserRepository()

    def check_rate_limit(self, user_id: str, action: str) -> tuple[bool, int, int, str]:
        """
        Check if user has exceeded rate limit

        Returns:
            (allowed, current_count, limit, message)
        """
        # Get user's plan limits
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return False, 0, 0, "User not found"

        limits = user.get('PlanLimits', {})

        if action == 'hint':
            limit = limits.get('max_hints_per_day', 5)
        elif action == 'execution':
            limit = limits.get('max_executions_per_day', 50)
        else:
            return False, 0, 0, "Invalid action"

        # Count today's usage
        current_count = self.usage_repo.count_today_usage(user_id, action)

        if current_count >= limit:
            return False, current_count, limit, f"Daily {action} limit exceeded"

        return True, current_count, limit, "OK"

    def log_usage(
        self,
        user_id: str,
        action: str,
        problem_id: str = None,
        problem_pk: str = None,
        metadata: dict = None
    ):
        """Log a usage action"""
        return self.usage_repo.log_usage(
            user_id=user_id,
            action=action,
            problem_id=problem_id,
            problem_pk=problem_pk,
            metadata=metadata
        )


# Usage example
def execute_code_with_rate_limit(user_id: str, problem_id: str, code: str):
    rate_limiter = RateLimiter()

    # Check rate limit
    allowed, current_count, limit, message = rate_limiter.check_rate_limit(
        user_id, 'execution'
    )

    if not allowed:
        raise Exception(f"Rate limit exceeded: {message}")

    # Execute code (omitted for brevity)
    results = execute_code_logic(problem_id, code)

    # Log usage
    rate_limiter.log_usage(
        user_id=user_id,
        action='execution',
        problem_id=problem_id,
        metadata={'language': 'python', 'execution_time': 150}
    )

    return results
```

### Pagination Helper

```python
# utils/pagination.py
from typing import Dict, Optional, List, Callable
import base64
import json


class Paginator:
    """Helper for DynamoDB pagination"""

    @staticmethod
    def encode_last_key(last_key: Optional[Dict]) -> Optional[str]:
        """Encode LastEvaluatedKey to a pagination token"""
        if not last_key:
            return None

        json_str = json.dumps(last_key)
        return base64.b64encode(json_str.encode()).decode()

    @staticmethod
    def decode_last_key(token: Optional[str]) -> Optional[Dict]:
        """Decode pagination token to LastEvaluatedKey"""
        if not token:
            return None

        try:
            json_str = base64.b64decode(token.encode()).decode()
            return json.loads(json_str)
        except Exception:
            return None

    @staticmethod
    def paginate_all(
        query_func: Callable,
        limit_per_page: int = 100
    ) -> List[Dict]:
        """
        Paginate through all results

        Args:
            query_func: Function that accepts last_key and returns dict with
                       'items' and 'last_key'
        """
        all_items = []
        last_key = None

        while True:
            result = query_func(last_key=last_key)
            all_items.extend(result['items'])

            last_key = result.get('last_key')
            if not last_key:
                break

        return all_items


# Usage example
def get_all_user_history(user_id: str) -> List[Dict]:
    """Get all history for a user (automatically paginate)"""
    history_repo = SearchHistoryRepository()

    def query_func(last_key):
        return history_repo.get_user_history(
            user_id=user_id,
            limit=100,
            last_key=last_key
        )

    return Paginator.paginate_all(query_func)
```

---

## Migration Scripts

### Migrate Problems from PostgreSQL

```python
# migration/migrate_problems.py
import psycopg2
from repositories.problem_repository import ProblemRepository
from typing import List, Dict


def fetch_problems_from_postgres() -> List[Dict]:
    """Fetch all problems from PostgreSQL"""
    conn = psycopg2.connect(
        host="localhost",
        database="algoitny",
        user="postgres",
        password="password"
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id, platform, problem_id, title, problem_url,
            tags, solution_code, language, constraints,
            is_completed, is_deleted, deleted_at, deleted_reason,
            metadata, created_at
        FROM problems
        WHERE is_deleted = FALSE
    """)

    problems = []
    for row in cursor.fetchall():
        problems.append({
            'id': row[0],
            'platform': row[1],
            'problem_id': row[2],
            'title': row[3],
            'problem_url': row[4],
            'tags': row[5],
            'solution_code': row[6],
            'language': row[7],
            'constraints': row[8],
            'is_completed': row[9],
            'is_deleted': row[10],
            'deleted_at': row[11],
            'deleted_reason': row[12],
            'metadata': row[13],
            'created_at': row[14]
        })

    cursor.close()
    conn.close()

    return problems


def fetch_test_cases_from_postgres(problem_id: int) -> List[Dict]:
    """Fetch test cases for a problem"""
    conn = psycopg2.connect(
        host="localhost",
        database="algoitny",
        user="postgres",
        password="password"
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT input, output
        FROM test_cases
        WHERE problem_id = %s
        ORDER BY created_at
    """, (problem_id,))

    test_cases = []
    for row in cursor.fetchall():
        test_cases.append({
            'input': row[0],
            'output': row[1]
        })

    cursor.close()
    conn.close()

    return test_cases


def migrate_problems_to_dynamodb():
    """Migrate all problems and test cases to DynamoDB"""
    problem_repo = ProblemRepository()
    problems = fetch_problems_from_postgres()

    print(f"Migrating {len(problems)} problems...")

    for i, problem in enumerate(problems):
        try:
            # Create problem in DynamoDB
            problem_repo.create_problem(
                platform=problem['platform'],
                problem_id=problem['problem_id'],
                title=problem['title'],
                language=problem['language'],
                solution_code=problem.get('solution_code', ''),
                problem_url=problem.get('problem_url', ''),
                tags=problem.get('tags', []),
                constraints=problem.get('constraints', ''),
                is_completed=problem['is_completed']
            )

            # Migrate test cases
            test_cases = fetch_test_cases_from_postgres(problem['id'])
            if test_cases:
                problem_repo.create_test_cases(
                    platform=problem['platform'],
                    problem_id=problem['problem_id'],
                    test_cases=test_cases
                )

            print(f"Migrated {i+1}/{len(problems)}: {problem['platform']}#{problem['problem_id']}")

        except Exception as e:
            print(f"Error migrating problem {problem['id']}: {e}")
            continue

    print("Migration complete!")


if __name__ == '__main__':
    migrate_problems_to_dynamodb()
```

### Dual-Write Decorator

```python
# utils/dual_write.py
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def dual_write(dynamodb_func, postgres_func):
    """
    Decorator to write to both DynamoDB and PostgreSQL during migration

    Usage:
        @dual_write(
            dynamodb_func=lambda data: problem_repo.create_problem(**data),
            postgres_func=lambda data: Problem.objects.create(**data)
        )
        def create_problem(data):
            return data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get data from original function
            data = func(*args, **kwargs)

            # Write to PostgreSQL (primary for now)
            try:
                postgres_result = postgres_func(data)
                logger.info("PostgreSQL write successful")
            except Exception as e:
                logger.error(f"PostgreSQL write failed: {e}")
                raise

            # Write to DynamoDB (dual write)
            try:
                dynamodb_result = dynamodb_func(data)
                logger.info("DynamoDB write successful")
            except Exception as e:
                logger.error(f"DynamoDB write failed: {e}")
                # Don't fail the request, just log
                # We'll rely on PostgreSQL as source of truth

            return postgres_result

        return wrapper
    return decorator


# Usage example
problem_repo = ProblemRepository()

@dual_write(
    dynamodb_func=lambda data: problem_repo.create_problem(**data),
    postgres_func=lambda data: Problem.objects.create(**data)
)
def create_problem(data):
    """Create problem in both databases"""
    return data


# In Django view
def register_problem_view(request):
    data = {
        'platform': request.data['platform'],
        'problem_id': request.data['problem_id'],
        'title': request.data['title'],
        'language': request.data['language'],
        # ... other fields
    }

    result = create_problem(data)
    return Response(result)
```

---

## Testing Examples

### Unit Tests with Moto

```python
# tests/test_problem_repository.py
import pytest
from moto import mock_dynamodb
import boto3
from repositories.problem_repository import ProblemRepository


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing"""
    with mock_dynamodb():
        # Create table
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')

        dynamodb.create_table(
            TableName='AlgoItny-Main',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI1',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        )

        yield dynamodb


def test_create_problem(dynamodb_table):
    """Test creating a problem"""
    repo = ProblemRepository()

    problem = repo.create_problem(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        language='python',
        solution_code='a, b = map(int, input().split())\nprint(a + b)',
        is_completed=True
    )

    assert problem['Platform'] == 'baekjoon'
    assert problem['ProblemId'] == '1000'
    assert problem['Title'] == 'A+B'
    assert problem['IsCompleted'] is True


def test_get_problem(dynamodb_table):
    """Test retrieving a problem"""
    repo = ProblemRepository()

    # Create problem
    repo.create_problem(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        language='python',
        is_completed=True
    )

    # Retrieve problem
    problem = repo.get_problem('baekjoon', '1000')

    assert problem is not None
    assert problem['Title'] == 'A+B'


def test_create_test_cases(dynamodb_table):
    """Test creating test cases"""
    repo = ProblemRepository()

    # Create problem first
    repo.create_problem(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        language='python',
        is_completed=True
    )

    # Create test cases
    test_cases = [
        {'input': '1 2', 'output': '3'},
        {'input': '5 7', 'output': '12'},
        {'input': '10 20', 'output': '30'}
    ]

    repo.create_test_cases('baekjoon', '1000', test_cases)

    # Retrieve problem with test cases
    result = repo.get_problem_with_test_cases('baekjoon', '1000')

    assert len(result['test_cases']) == 3
    assert result['test_cases'][0]['Input'] == '1 2'
    assert result['test_cases'][0]['Output'] == '3'


def test_list_problems_by_platform(dynamodb_table):
    """Test listing problems by platform"""
    repo = ProblemRepository()

    # Create multiple problems
    for i in range(5):
        repo.create_problem(
            platform='baekjoon',
            problem_id=f'{1000 + i}',
            title=f'Problem {i}',
            language='python',
            is_completed=True
        )

    # List problems
    result = repo.list_problems_by_platform('baekjoon', limit=3)

    assert len(result['items']) == 3
    assert result['has_more'] is True
    assert result['last_key'] is not None
```

### Integration Test

```python
# tests/test_integration.py
import pytest
from repositories.problem_repository import ProblemRepository
from repositories.search_history_repository import SearchHistoryRepository
from repositories.usage_log_repository import UsageLogRepository


@pytest.mark.integration
def test_full_execution_flow():
    """Test complete code execution flow"""

    # 1. Create problem with test cases
    problem_repo = ProblemRepository()

    problem = problem_repo.create_problem(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        language='python',
        solution_code='a, b = map(int, input().split())\nprint(a + b)',
        is_completed=True
    )

    test_cases = [
        {'input': '1 2', 'output': '3'},
        {'input': '5 7', 'output': '12'}
    ]

    problem_repo.create_test_cases('baekjoon', '1000', test_cases)

    # 2. Log usage
    usage_repo = UsageLogRepository()
    user_id = 'test-user-123'

    usage_repo.log_usage(
        user_id=user_id,
        action='execution',
        problem_pk=problem['PK'],
        problem_id=problem['InternalId']
    )

    # 3. Create search history
    history_repo = SearchHistoryRepository()

    history = history_repo.create_search_history(
        user_id=user_id,
        user_identifier='test@example.com',
        problem_pk=problem['PK'],
        problem_id=problem['InternalId'],
        platform='baekjoon',
        problem_number='1000',
        problem_title='A+B',
        language='python',
        code='a, b = map(int, input().split())\nprint(a + b)',
        result_summary={'passed': 2, 'failed': 0},
        passed_count=2,
        failed_count=0,
        total_count=2,
        is_code_public=True
    )

    # 4. Verify everything
    assert problem is not None
    assert history is not None

    # Check usage count
    count = usage_repo.count_today_usage(user_id, 'execution')
    assert count == 1

    # Check user history
    user_history = history_repo.get_user_history(user_id, limit=10)
    assert len(user_history['items']) == 1

    # Check public history
    public_history = history_repo.get_public_history(limit=10)
    assert len(public_history['items']) == 1
```

---

**Last Updated:** 2025-01-15
**Version:** 1.0

## Next Steps

1. Run table creation scripts in development environment
2. Implement repositories in your Django application
3. Write unit tests for all repositories
4. Set up DynamoDB Local for local development
5. Begin dual-write implementation for gradual migration
