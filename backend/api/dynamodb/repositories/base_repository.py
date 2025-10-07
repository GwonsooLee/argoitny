"""Base repository for DynamoDB operations"""
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key, Attr


class BaseRepository:
    """Base repository with common DynamoDB operations"""

    def __init__(self, table):
        """
        Initialize repository

        Args:
            table: DynamoDB table resource
        """
        self.table = table

    def _to_dynamodb_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Python types to DynamoDB types

        Args:
            data: Dictionary with Python types

        Returns:
            Dictionary with DynamoDB-compatible types
        """
        result = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, float):
                result[key] = Decimal(str(value))
            elif isinstance(value, dict):
                result[key] = self._to_dynamodb_item(value)
            elif isinstance(value, list):
                result[key] = [
                    self._to_dynamodb_item(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def _from_dynamodb_item(self, item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Convert DynamoDB types to Python types

        Args:
            item: DynamoDB item

        Returns:
            Dictionary with Python types
        """
        if not item:
            return None

        result = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                result[key] = int(value) if value % 1 == 0 else float(value)
            elif isinstance(value, dict):
                result[key] = self._from_dynamodb_item(value)
            elif isinstance(value, list):
                result[key] = [
                    self._from_dynamodb_item(v) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Put item into table

        Args:
            item: Item to insert

        Returns:
            Inserted item
        """
        dynamodb_item = self._to_dynamodb_item(item)
        self.table.put_item(Item=dynamodb_item)
        return item

    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """
        Get item by primary key

        Args:
            pk: Partition key
            sk: Sort key

        Returns:
            Item or None if not found
        """
        response = self.table.get_item(Key={'PK': pk, 'SK': sk})
        return self._from_dynamodb_item(response.get('Item'))

    def query(
        self,
        key_condition_expression,
        filter_expression=None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query items

        Args:
            key_condition_expression: Key condition expression
            filter_expression: Optional filter expression
            index_name: Optional GSI name
            limit: Maximum items to return
            scan_index_forward: Sort order (True = ascending, False = descending)
            **kwargs: Additional query parameters

        Returns:
            List of items
        """
        query_params = {
            'KeyConditionExpression': key_condition_expression,
            'ScanIndexForward': scan_index_forward
        }

        if filter_expression is not None:
            query_params['FilterExpression'] = filter_expression

        if index_name:
            query_params['IndexName'] = index_name

        if limit:
            query_params['Limit'] = limit

        query_params.update(kwargs)

        response = self.table.query(**query_params)
        return [self._from_dynamodb_item(item) for item in response.get('Items', [])]

    def scan(
        self,
        filter_expression=None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scan items (expensive operation, use sparingly)

        Args:
            filter_expression: Optional filter expression
            limit: Maximum items to return
            **kwargs: Additional scan parameters

        Returns:
            List of items
        """
        scan_params = {}

        if filter_expression is not None:
            scan_params['FilterExpression'] = filter_expression

        if limit:
            scan_params['Limit'] = limit

        scan_params.update(kwargs)

        response = self.table.scan(**scan_params)
        return [self._from_dynamodb_item(item) for item in response.get('Items', [])]

    def update_item(
        self,
        pk: str,
        sk: str,
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Update item

        Args:
            pk: Partition key
            sk: Sort key
            update_expression: Update expression
            expression_attribute_values: Values for update expression
            expression_attribute_names: Optional attribute name mappings

        Returns:
            Updated item
        """
        update_params = {
            'Key': {'PK': pk, 'SK': sk},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': self._to_dynamodb_item(expression_attribute_values),
            'ReturnValues': 'ALL_NEW'
        }

        if expression_attribute_names:
            update_params['ExpressionAttributeNames'] = expression_attribute_names

        response = self.table.update_item(**update_params)
        return self._from_dynamodb_item(response.get('Attributes'))

    def delete_item(self, pk: str, sk: str) -> bool:
        """
        Delete item

        Args:
            pk: Partition key
            sk: Sort key

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.table.delete_item(Key={'PK': pk, 'SK': sk})
            return True
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False

    def batch_write(self, items: List[Dict[str, Any]]) -> bool:
        """
        Batch write items (max 25 items per batch)

        Args:
            items: List of items to write

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    dynamodb_item = self._to_dynamodb_item(item)
                    batch.put_item(Item=dynamodb_item)
            return True
        except Exception as e:
            print(f"Error in batch write: {e}")
            return False

    @staticmethod
    def get_timestamp() -> int:
        """Get current Unix timestamp"""
        return int(time.time())
