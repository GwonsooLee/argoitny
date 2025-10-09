"""
SubscriptionPlan Repository - DynamoDB Implementation

Data Structure:
- PK: PLAN#{plan_id}
- SK: META
- Type: plan
- Data: {plan details with short field names}
"""
import time
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from .base_repository import BaseRepository


class SubscriptionPlanRepository(BaseRepository):
    """Repository for SubscriptionPlan operations in DynamoDB"""

    def __init__(self, table=None):
        """
        Initialize SubscriptionPlanRepository

        Args:
            table: DynamoDB table resource. If None, will be fetched from DynamoDBClient
        """
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

    def create_plan(self, plan_data: Dict) -> Dict:
        """
        Create a new subscription plan

        Args:
            plan_data: Dictionary with plan details
                - id: Plan ID
                - name: Plan name
                - max_hints_per_day: Maximum hints per day (-1 for unlimited)
                - max_executions_per_day: Maximum executions per day (-1 for unlimited)
                - price: Price (optional, default 0)
                - is_active: Active status (optional, default True)

        Returns:
            Created plan data
        """
        plan_id = plan_data['id']
        timestamp = int(time.time())

        # Prepare item with short field names for storage efficiency
        # Note: plan_id is stored in PK, not in dat (to avoid redundancy)
        item = {
            'PK': f'PLAN#{plan_id}',
            'SK': 'META',
            'tp': 'plan',  # type
            'dat': {
                'nm': plan_data['name'],  # name
                'dsc': plan_data.get('description', ''),  # description
                'mh': plan_data['max_hints_per_day'],  # max_hints_per_day
                'me': plan_data['max_executions_per_day'],  # max_executions_per_day
                'mp': plan_data.get('max_problems', -1),  # max_problems
                'cva': plan_data.get('can_view_all_problems', True),  # can_view_all_problems
                'crp': plan_data.get('can_register_problems', False),  # can_register_problems
                'prc': plan_data.get('price', 0),  # price
                'act': plan_data.get('is_active', True),  # is_active
            },
            'crt': timestamp,  # created_at
            'upd': timestamp,  # updated_at
        }

        self.table.put_item(Item=item)

        return self._transform_to_long_format(item)

    def get_plan(self, plan_id: int) -> Optional[Dict]:
        """
        Get subscription plan by ID

        Args:
            plan_id: Plan ID

        Returns:
            Plan data with long field names, or None if not found
        """
        try:
            response = self.table.get_item(
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

    def list_plans(self, limit: int = 100) -> List[Dict]:
        """
        List all subscription plans using Scan

        Note: Uses Scan instead of Query because SubscriptionPlan is configuration data
        with only ~5 items (static). Scan cost is negligible for this use case.

        Args:
            limit: Maximum number of plans to return

        Returns:
            List of plans with long field names
        """
        try:
            # Use Scan with filter since subscription plans are few (5 items max)
            # and don't populate GSI1 attributes
            from boto3.dynamodb.conditions import Attr

            items = self.scan(
                filter_expression=Attr('tp').eq('plan') & Attr('SK').eq('META'),
                limit=limit
            )

            plans = []
            for item in items:
                plans.append(self._transform_to_long_format(item))

            return plans

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return []
            raise

    def update_plan(self, plan_id: int, updates: Dict) -> Dict:
        """
        Update subscription plan

        Args:
            plan_id: Plan ID
            updates: Dictionary with fields to update (using long field names)

        Returns:
            Updated plan data
        """
        # Map long field names to short field names
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
                # Use nested attribute syntax: #dat.#field_name
                attr_name_dat = '#dat'
                attr_name_field = f'#dat_{short_name}'
                attr_value = f':val_{short_name}'

                update_expression_parts.append(f'{attr_name_dat}.{attr_name_field} = {attr_value}')
                expression_attribute_names[attr_name_dat] = 'dat'
                expression_attribute_names[attr_name_field] = short_name
                expression_attribute_values[attr_value] = value

        # Always update timestamp
        update_expression_parts.append('#upd = :upd')
        expression_attribute_names['#upd'] = 'upd'
        expression_attribute_values[':upd'] = int(time.time())

        update_expression = 'SET ' + ', '.join(update_expression_parts)

        response = self.table.update_item(
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

    def delete_plan(self, plan_id: int) -> bool:
        """
        Delete subscription plan

        Args:
            plan_id: Plan ID

        Returns:
            True if deleted successfully
        """
        try:
            self.table.delete_item(
                Key={
                    'PK': f'PLAN#{plan_id}',
                    'SK': 'META'
                }
            )
            return True

        except ClientError:
            return False

    def _transform_to_long_format(self, item: Dict) -> Dict:
        """
        Transform DynamoDB item with short field names to long field names

        Args:
            item: DynamoDB item with short field names

        Returns:
            Dictionary with long field names
        """
        dat = item.get('dat', {})

        # Extract plan_id from PK (format: PLAN#{plan_id})
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
