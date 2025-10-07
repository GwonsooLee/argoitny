"""Rate limiting utilities"""
from django.utils import timezone
from datetime import timedelta
from api.models import UsageLog


def check_rate_limit(user, action):
    """
    Check if user has exceeded rate limit for the given action

    Args:
        user: User instance
        action: 'hint' or 'execution'

    Returns:
        tuple: (allowed: bool, current_count: int, limit: int, message: str)
    """
    # Admin users have unlimited access
    if user.is_admin():
        return True, 0, -1, "Admin users have unlimited access"

    # Get user's plan limits
    limits = user.get_plan_limits()

    if action == 'hint':
        limit = limits['max_hints_per_day']
    elif action == 'execution':
        limit = limits['max_executions_per_day']
    else:
        return False, 0, 0, f"Invalid action: {action}"

    # Unlimited access (-1)
    if limit == -1:
        return True, 0, -1, "Unlimited access"

    # Get today's usage count
    today = timezone.now().date()
    today_start = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.min.time())
    )

    current_count = UsageLog.objects.filter(
        user=user,
        action=action,
        created_at__gte=today_start
    ).count()

    if current_count >= limit:
        return False, current_count, limit, \
            f"Daily {action} limit exceeded ({current_count}/{limit})"

    return True, current_count, limit, \
        f"Within limit ({current_count}/{limit})"


def log_usage(user, action, problem=None, metadata=None):
    """
    Log usage for rate limiting

    Args:
        user: User instance
        action: 'hint' or 'execution'
        problem: Problem instance (optional)
        metadata: dict with additional context (optional)
    """
    UsageLog.objects.create(
        user=user,
        action=action,
        problem=problem,
        metadata=metadata or {}
    )
