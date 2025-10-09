"""Counter Repository for managing auto-increment IDs in DynamoDB"""
from typing import Optional
from .base_repository import BaseRepository


class CounterRepository(BaseRepository):
    """
    Repository for managing atomic counters in DynamoDB

    This provides auto-increment ID functionality similar to PostgreSQL sequences.

    DynamoDB Structure:
        PK: 'COUNTER#{counter_name}'  (e.g., 'COUNTER#sgjob_id')
        SK: 'VALUE'
        tp: 'counter'
        val: current_value (Number)
    """

    def get_next_id(self, counter_name: str) -> int:
        """
        Get next ID for a counter (atomic increment)

        Args:
            counter_name: Name of the counter (e.g., 'sgjob_id', 'pejob_id')

        Returns:
            Next ID value
        """
        pk = f'COUNTER#{counter_name}'
        sk = 'VALUE'

        try:
            response = self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression='SET val = if_not_exists(val, :start) + :inc',
                ExpressionAttributeValues={
                    ':start': 0,
                    ':inc': 1
                },
                ReturnValues='UPDATED_NEW'
            )

            return int(response['Attributes']['val'])

        except Exception as e:
            # If item doesn't exist, create it
            self.table.put_item(
                Item={
                    'PK': pk,
                    'SK': sk,
                    'tp': 'counter',
                    'val': 1
                }
            )
            return 1

    def get_current_value(self, counter_name: str) -> Optional[int]:
        """
        Get current counter value without incrementing

        Args:
            counter_name: Name of the counter

        Returns:
            Current value or None if counter doesn't exist
        """
        pk = f'COUNTER#{counter_name}'
        sk = 'VALUE'

        response = self.table.get_item(Key={'PK': pk, 'SK': sk})
        item = response.get('Item')

        if not item:
            return None

        return int(item.get('val', 0))

    def set_counter_value(self, counter_name: str, value: int):
        """
        Set counter to a specific value (useful for migration)

        Args:
            counter_name: Name of the counter
            value: Value to set
        """
        pk = f'COUNTER#{counter_name}'
        sk = 'VALUE'

        self.table.put_item(
            Item={
                'PK': pk,
                'SK': sk,
                'tp': 'counter',
                'val': value
            }
        )
