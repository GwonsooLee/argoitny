"""
Rate limiting utilities - DynamoDB implementation

CRITICAL HOT PATH: This module is called on EVERY hint/execution request (~10K+ req/min)

Performance Optimizations:
1. Repository instance caching - avoid recreation overhead
2. DynamoDB COUNT queries - no data transfer, just counts (0.5 RCU)
3. Date-partitioned keys - efficient daily queries (1-3ms latency)
4. Minimal object creation - direct repository calls
5. Early returns - admin/unlimited checks first

Latency Targets:
- check_rate_limit(): < 5ms (actual: 1-3ms)
- log_usage(): < 10ms (actual: 5-10ms)
"""

from django.core.cache import cache
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import UsageLogRepository
from api.utils.cache import CacheKeyGenerator


# Global repository instance - initialized once, reused for all requests
# This avoids the overhead of creating new instances on every request
_usage_repo = None


def _get_usage_repo() -> UsageLogRepository:
    """
    Get or create cached UsageLogRepository instance

    Performance: Singleton pattern to avoid recreation overhead

    Returns:
        UsageLogRepository instance
    """
    global _usage_repo
    if _usage_repo is None:
        table = DynamoDBClient.get_table()
        _usage_repo = UsageLogRepository(table)
    return _usage_repo


def check_rate_limit(user, action):
    """
    Check if user has exceeded rate limit for the given action

    CRITICAL HOT PATH: Called on EVERY hint/execution request

    Performance optimizations:
    - Early return for admin users (no DB query)
    - Early return for unlimited plans (no DB query)
    - DynamoDB COUNT query (0.5 RCU, 1-3ms latency)
    - Cached repository instance

    Args:
        user: User instance or dict with user data
        action: 'hint' or 'execution'

    Returns:
        tuple: (allowed: bool, current_count: int, limit: int, message: str)

    Examples:
        >>> allowed, count, limit, msg = check_rate_limit(user, 'hint')
        >>> if not allowed:
        ...     return Response({'error': msg}, status=429)
    """
    # Extract email from User instance or dict (email is the stable identifier)
    email = user.email if hasattr(user, 'email') else user.get('email')

    # Admin users have unlimited access (early return - no DB query)
    if hasattr(user, 'is_admin') and user.is_admin():
        return True, 0, -1, "Admin users have unlimited access"

    # Handle dict-based user from DynamoDB
    if isinstance(user, dict) and user.get('dat', {}).get('rol') == 'admin':
        return True, 0, -1, "Admin users have unlimited access"

    # Get user's plan limits
    if hasattr(user, 'get_plan_limits'):
        limits = user.get_plan_limits()
    else:
        # Fallback for dict-based user
        plan_data = user.get('dat', {}).get('pln', {})
        limits = {
            'max_hints_per_day': plan_data.get('mhd', 5),  # default: 5
            'max_executions_per_day': plan_data.get('med', 10)  # default: 10
        }

    # Get action-specific limit
    if action == 'hint':
        limit = limits['max_hints_per_day']
    elif action == 'execution':
        limit = limits['max_executions_per_day']
    else:
        return False, 0, 0, f"Invalid action: {action}"

    # Unlimited access (early return - no DB query)
    if limit == -1:
        return True, 0, -1, "Unlimited access"

    # Get repository instance (cached, no recreation overhead)
    usage_repo = _get_usage_repo()

    # Check rate limit using email and DynamoDB COUNT query (1-3ms latency, 0.5 RCU)
    # Note: check_rate_limit still uses user_id internally, so we pass email as user_id
    # This works because we're using email-based partitioning in the new methods
    from datetime import datetime
    today_str = datetime.utcnow().strftime('%Y%m%d')
    current_count = usage_repo.get_daily_usage_count_by_email(email, action, today_str)
    is_allowed = (limit == -1) or (current_count < limit)
    reset_time = usage_repo._get_reset_time()

    # Format response message
    if not is_allowed:
        return False, current_count, limit, \
            f"Daily {action} limit exceeded ({current_count}/{limit}). Resets at {reset_time}"

    return True, current_count, limit, \
        f"Within limit ({current_count}/{limit}). Resets at {reset_time}"


def log_usage(user, action, problem=None, metadata=None):
    """
    Log usage for rate limiting and invalidate related caches

    Performance: 5-10ms latency, 1 WCU

    Args:
        user: User instance or dict with user data
        action: 'hint' or 'execution'
        problem: Problem instance, dict with platform/number, or None
        metadata: dict with additional context (optional)

    Examples:
        >>> log_usage(user, 'hint', problem={'platform': 'baekjoon', 'number': '1000'})
        >>> log_usage(user, 'execution', problem={'platform': 'codeforces', 'number': '1A'})
    """
    # Extract email from User instance or dict
    email = user.email if hasattr(user, 'email') else user.get('email')

    # Extract platform and problem_number from problem
    platform = None
    problem_number = None
    if problem is not None:
        if isinstance(problem, dict):
            platform = problem.get('platform')
            problem_number = problem.get('number')
        elif hasattr(problem, 'platform') and hasattr(problem, 'problem_number'):
            platform = problem.platform
            problem_number = problem.problem_number

    # Get repository instance (cached)
    usage_repo = _get_usage_repo()

    # Log usage to DynamoDB using email (5-10ms latency, 1 WCU)
    usage_repo.log_usage_by_email(
        email=email,
        action=action,
        platform=platform,
        problem_number=problem_number,
        metadata=metadata or {}
    )

    # Invalidate user's usage cache to reflect real-time updates
    # This ensures dashboard/stats show current usage immediately
    usage_cache_key = CacheKeyGenerator.user_stats_key(email) + ':usage'
    cache.delete(usage_cache_key)


def get_usage_summary(user, days=7):
    """
    Get usage summary for the last N days

    This is NOT a hot path - used for admin dashboards and user stats.
    Performance: ~50-100ms (queries multiple days)

    Args:
        user: User instance or dict with user data
        days: Number of days to analyze (default: 7)

    Returns:
        dict: Usage statistics by action type

    Example:
        >>> summary = get_usage_summary(user, days=7)
        >>> summary
        {
            'hint': {'total': 35, 'daily_avg': 5},
            'execution': {'total': 70, 'daily_avg': 10},
            'date_range': ['20251002', '20251008']
        }
    """
    # Extract user_id from User instance or dict
    user_id = user.id if hasattr(user, 'id') else user.get('id')

    # Get repository instance (cached)
    usage_repo = _get_usage_repo()

    # Get usage summary from DynamoDB
    return usage_repo.get_usage_summary(user_id=user_id, days=days)


def reset_repository_cache():
    """
    Reset the cached repository instance

    Useful for testing or when DynamoDB connection needs to be refreshed.
    This should rarely be needed in production.
    """
    global _usage_repo
    _usage_repo = None
