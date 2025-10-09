"""User repository for DynamoDB operations"""
from typing import Dict, Optional, List, Any
from boto3.dynamodb.conditions import Key, Attr
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for User entity operations"""

    def __init__(self, table=None):
        """
        Initialize UserRepository

        Args:
            table: DynamoDB table resource. If None, will be fetched from DynamoDBClient
        """
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user

        Args:
            user_data: User data dict with keys:
                - user_id: User ID (integer)
                - email: User email (string)
                - name: User name (string, optional)
                - picture: Picture URL (string, optional)
                - google_id: Google OAuth ID (string, optional)
                - subscription_plan_id: Plan ID (integer, optional)
                - is_active: Active status (boolean, default True)
                - is_staff: Staff status (boolean, default False)

        Returns:
            Created user dict with all attributes
        """
        user_id = user_data['user_id']
        email = user_data['email']
        timestamp = self.get_timestamp()

        # Build the dat map with short field names
        dat = {
            'em': email,
            'nm': user_data.get('name', ''),
            'pic': user_data.get('picture', ''),
            'gid': user_data.get('google_id', ''),
            'plan': user_data.get('subscription_plan_id'),
            'act': user_data.get('is_active', True),
            'stf': user_data.get('is_staff', False)
        }

        # Create the DynamoDB item
        item = {
            'PK': f'USR#{user_id}',
            'SK': 'META',
            'tp': 'usr',
            'dat': dat,
            'crt': timestamp,
            'upd': timestamp,
            'GSI1PK': f'EMAIL#{email}',
            'GSI1SK': f'USR#{user_id}'
        }

        # Add GSI2 for Google ID if provided
        if user_data.get('google_id'):
            item['GSI2PK'] = f'GID#{user_data["google_id"]}'

        self.put_item(item)

        # Return normalized user data
        return self._item_to_user_dict(item)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User dict or None if not found
        """
        item = self.get_item(f'USR#{user_id}', 'META')
        if not item:
            return None

        return self._item_to_user_dict(item)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email (uses GSI1)

        Args:
            email: User email

        Returns:
            User dict or None if not found
        """
        results = self.query(
            key_condition_expression=Key('GSI1PK').eq(f'EMAIL#{email}'),
            index_name='GSI1'
        )

        if not results:
            return None

        return self._item_to_user_dict(results[0])

    def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Google ID (uses GSI2)

        Args:
            google_id: Google OAuth ID

        Returns:
            User dict or None if not found
        """
        results = self.query(
            key_condition_expression=Key('GSI2PK').eq(f'GID#{google_id}'),
            index_name='GSI2'
        )

        if not results:
            return None

        return self._item_to_user_dict(results[0])

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user attributes

        Args:
            user_id: User ID
            updates: Dict of attributes to update. Supported keys:
                - name: User name
                - picture: Picture URL
                - google_id: Google OAuth ID
                - subscription_plan_id: Plan ID
                - is_active: Active status
                - is_staff: Staff status
                - email: Email (updates GSI1PK as well)

        Returns:
            Updated user dict
        """
        # Map long field names to short names
        field_mapping = {
            'name': 'nm',
            'picture': 'pic',
            'google_id': 'gid',
            'subscription_plan_id': 'plan',
            'is_active': 'act',
            'is_staff': 'stf',
            'email': 'em'
        }

        # Build update expression for dat fields
        update_parts = []
        attr_values = {}
        attr_names = {}

        # Add timestamp update
        update_parts.append('#upd = :upd')
        attr_names['#upd'] = 'upd'
        attr_values[':upd'] = self.get_timestamp()

        # Handle email update (requires GSI1PK update)
        if 'email' in updates:
            update_parts.append('GSI1PK = :gsi1pk')
            attr_values[':gsi1pk'] = f'EMAIL#{updates["email"]}'

        # Handle google_id update (requires GSI2PK update/removal)
        if 'google_id' in updates:
            if updates['google_id']:
                update_parts.append('GSI2PK = :gsi2pk')
                attr_values[':gsi2pk'] = f'GID#{updates["google_id"]}'
            else:
                # Remove GSI2PK if google_id is cleared
                update_parts.append('REMOVE GSI2PK')

        # Build dat updates using nested attribute syntax
        for key, value in updates.items():
            if key in field_mapping:
                short_key = field_mapping[key]
                attr_name_field = f'#dat_{short_key}'
                attr_value = f':dat_{short_key}'

                update_parts.append(f'#dat.{attr_name_field} = {attr_value}')
                attr_names['#dat'] = 'dat'
                attr_names[attr_name_field] = short_key
                attr_values[attr_value] = value

        if not update_parts:
            # No updates, just return current user
            return self.get_user_by_id(user_id)

        update_expression = 'SET ' + ', '.join(update_parts)

        # Perform update
        updated_item = self.update_item(
            pk=f'USR#{user_id}',
            sk='META',
            update_expression=update_expression,
            expression_attribute_values=attr_values,
            expression_attribute_names=attr_names if attr_names else None
        )

        return self._item_to_user_dict(updated_item)

    def update_subscription_plan(self, user_id: int, plan_id: int) -> Dict[str, Any]:
        """
        Update user's subscription plan

        Args:
            user_id: User ID
            plan_id: Subscription plan ID

        Returns:
            Updated user dict
        """
        return self.update_user(user_id, {'subscription_plan_id': plan_id})

    def list_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all users (scan operation - expensive, use sparingly)

        Args:
            limit: Maximum number of users to return

        Returns:
            List of user dicts
        """
        items = self.scan(
            filter_expression=Attr('tp').eq('usr') & Attr('SK').eq('META'),
            limit=limit
        )

        return [self._item_to_user_dict(item) for item in items]

    def list_active_users(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        List all active users (scan operation - expensive, use sparingly)

        Args:
            limit: Maximum number of users to return

        Returns:
            List of active user dicts
        """
        items = self.scan(
            filter_expression=Attr('tp').eq('usr') & Attr('SK').eq('META') & Attr('dat.act').eq(True),
            limit=limit
        )

        return [self._item_to_user_dict(item) for item in items]

    def is_admin(self, user_id: int, admin_emails: List[str]) -> bool:
        """
        Check if user is an admin (by email or is_staff flag)

        Args:
            user_id: User ID
            admin_emails: List of admin email addresses

        Returns:
            True if user is admin, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Check if user is staff
        if user.get('is_staff'):
            return True

        # Check if email is in admin list
        return user.get('email') in admin_emails

    def _item_to_user_dict(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DynamoDB item to normalized user dict

        Args:
            item: DynamoDB item

        Returns:
            Normalized user dict with long field names
        """
        dat = item.get('dat', {})
        user_id = item['PK'].replace('USR#', '')

        return {
            'user_id': int(user_id),
            'email': dat.get('em', ''),
            'name': dat.get('nm', ''),
            'picture': dat.get('pic', ''),
            'google_id': dat.get('gid', ''),
            'subscription_plan_id': dat.get('plan'),
            'is_active': dat.get('act', True),
            'is_staff': dat.get('stf', False),
            'created_at': item.get('crt'),
            'updated_at': item.get('upd')
        }

    def delete_user(self, user_id: int) -> bool:
        """
        Delete user (soft delete by setting is_active=False is recommended)

        Args:
            user_id: User ID

        Returns:
            True if deleted, False otherwise
        """
        return self.delete_item(f'USR#{user_id}', 'META')

    def get_users_by_plan(self, plan_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all users with a specific subscription plan (scan operation)

        Args:
            plan_id: Subscription plan ID
            limit: Maximum number of users to return

        Returns:
            List of user dicts
        """
        items = self.scan(
            filter_expression=(
                Attr('tp').eq('usr') &
                Attr('SK').eq('META') &
                Attr('dat.plan').eq(plan_id) &
                Attr('dat.act').eq(True)
            ),
            limit=limit
        )

        return [self._item_to_user_dict(item) for item in items]

    def batch_create_users(self, users_data: List[Dict[str, Any]]) -> bool:
        """
        Batch create multiple users (max 25 per batch)

        Args:
            users_data: List of user data dicts

        Returns:
            True if successful, False otherwise
        """
        items = []
        timestamp = self.get_timestamp()

        for user_data in users_data:
            user_id = user_data['user_id']
            email = user_data['email']

            dat = {
                'em': email,
                'nm': user_data.get('name', ''),
                'pic': user_data.get('picture', ''),
                'gid': user_data.get('google_id', ''),
                'plan': user_data.get('subscription_plan_id'),
                'act': user_data.get('is_active', True),
                'stf': user_data.get('is_staff', False)
            }

            item = {
                'PK': f'USR#{user_id}',
                'SK': 'META',
                'tp': 'usr',
                'dat': dat,
                'crt': timestamp,
                'upd': timestamp,
                'GSI1PK': f'EMAIL#{email}',
                'GSI1SK': f'USR#{user_id}'
            }

            if user_data.get('google_id'):
                item['GSI2PK'] = f'GID#{user_data["google_id"]}'

            items.append(item)

        return self.batch_write(items)

    def user_exists(self, email: str) -> bool:
        """
        Check if user exists by email

        Args:
            email: User email

        Returns:
            True if user exists, False otherwise
        """
        user = self.get_user_by_email(email)
        return user is not None

    def activate_user(self, user_id: int) -> Dict[str, Any]:
        """
        Activate user account

        Args:
            user_id: User ID

        Returns:
            Updated user dict
        """
        return self.update_user(user_id, {'is_active': True})

    def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        """
        Deactivate user account (soft delete)

        Args:
            user_id: User ID

        Returns:
            Updated user dict
        """
        return self.update_user(user_id, {'is_active': False})
