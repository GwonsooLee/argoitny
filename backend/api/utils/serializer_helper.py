"""Serializer Helper for DynamoDB Users - ASYNC VERSION"""
from typing import Dict, Any
from django.conf import settings


async def serialize_dynamodb_user(user_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize DynamoDB user dict to match UserSerializer output format (ASYNC)

    Args:
        user_dict: User data dictionary from UserRepository

    Returns:
        Dict matching UserSerializer output format
    """
    # Get subscription plan details from DynamoDB if plan_id exists
    plan_name = None
    plan_description = None
    subscription_plan_id = user_dict.get('subscription_plan_id')

    if subscription_plan_id:
        try:
            from ..dynamodb.async_client import AsyncDynamoDBClient
            from ..dynamodb.async_repositories import AsyncSubscriptionPlanRepository

            async with AsyncDynamoDBClient.get_resource() as resource:
                table = await resource.Table(AsyncDynamoDBClient._table_name)
                plan_repo = AsyncSubscriptionPlanRepository(table)
                plan = await plan_repo.get_plan(subscription_plan_id)

            if plan:
                plan_name = plan.get('name')
                plan_description = plan.get('description')
        except Exception:
            pass

    # Check if user is admin
    is_admin = user_dict.get('is_staff', False)
    if not is_admin and user_dict.get('email'):
        is_admin = user_dict['email'] in settings.ADMIN_EMAILS

    return {
        'id': user_dict.get('user_id'),
        'email': user_dict.get('email', ''),
        'name': user_dict.get('name', ''),
        'picture': user_dict.get('picture', ''),
        'is_admin': is_admin,
        'subscription_plan_name': plan_name,
        'subscription_plan_description': plan_description,
        'created_at': user_dict.get('created_at'),
    }
