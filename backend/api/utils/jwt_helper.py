"""JWT Token Helper for DynamoDB Users"""
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Dict, Any


class DynamoDBUser:
    """
    Wrapper class to make DynamoDB user dict compatible with JWT token generation.

    This class wraps a user dict from DynamoDB and provides the interface
    that rest_framework_simplejwt expects for token generation.
    """

    def __init__(self, user_dict: Dict[str, Any]):
        """
        Initialize with user dict from DynamoDB repository

        Args:
            user_dict: User data dictionary from UserRepository
        """
        self._data = user_dict

    @property
    def pk(self):
        """Primary key for JWT token - returns email (stable identifier)"""
        return self._data.get('email')

    @property
    def id(self):
        """User ID - returns email (stable identifier)"""
        return self._data.get('email')

    @property
    def email(self):
        """User email"""
        return self._data.get('email', '')

    @property
    def name(self):
        """User name"""
        return self._data.get('name', '')

    @property
    def is_active(self):
        """Active status"""
        return self._data.get('is_active', True)

    @property
    def is_staff(self):
        """Staff status"""
        return self._data.get('is_staff', False)

    def __getattr__(self, name):
        """
        Fallback for any attribute not explicitly defined.
        Returns value from user dict or None.
        """
        return self._data.get(name)

    def __getitem__(self, key):
        """Allow dict-like access"""
        return self._data[key]

    def get(self, key, default=None):
        """Dict-like get method"""
        return self._data.get(key, default)


def generate_tokens_for_user(user_dict: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate JWT tokens for a DynamoDB user dict

    Args:
        user_dict: User data dictionary from UserRepository

    Returns:
        Dict containing 'access' and 'refresh' token strings
    """
    user_wrapper = DynamoDBUser(user_dict)
    refresh = RefreshToken.for_user(user_wrapper)

    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }
