"""
Cache utilities for Django backend

This module provides caching decorators, utilities, and helpers for implementing
a comprehensive caching strategy with Redis.
"""
import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet
from django.http import JsonResponse
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Generate consistent cache keys for different data types"""

    @staticmethod
    def make_key(prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from prefix and arguments

        Args:
            prefix: Cache key prefix (e.g., 'problem_list', 'user_stats')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            str: Generated cache key
        """
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())

        # Create a unique string from args and kwargs
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted_kwargs])

        # Create hash if key is too long
        if key_parts:
            params_str = ":".join(key_parts)
            if len(params_str) > 100:
                params_hash = hashlib.md5(params_str.encode()).hexdigest()
                return f"{prefix}:{params_hash}"
            return f"{prefix}:{params_str}"

        return prefix

    @staticmethod
    def problem_list_key(platform: Optional[str] = None, search: Optional[str] = None,
                        page: int = 1, **filters) -> str:
        """Generate cache key for problem list"""
        return CacheKeyGenerator.make_key(
            'problem_list',
            platform=platform or 'all',
            search=search or 'none',
            page=page,
            **filters
        )

    @staticmethod
    def problem_detail_key(problem_id: Optional[int] = None,
                          platform: Optional[str] = None,
                          problem_identifier: Optional[str] = None) -> str:
        """Generate cache key for problem detail"""
        if problem_id:
            return f"problem_detail:id:{problem_id}"
        return f"problem_detail:platform:{platform}:{problem_identifier}"

    @staticmethod
    def user_stats_key(user_id: int) -> str:
        """Generate cache key for user statistics"""
        return f"user_stats:{user_id}"

    @staticmethod
    def search_history_key(user_id: Optional[int] = None,
                          user_identifier: Optional[str] = None,
                          page: int = 1) -> str:
        """Generate cache key for search history"""
        identifier = user_id or user_identifier or 'anonymous'
        return f"search_history:{identifier}:page:{page}"

    @staticmethod
    def test_cases_key(problem_id: int) -> str:
        """Generate cache key for test cases"""
        return f"test_cases:problem:{problem_id}"


def cache_response(timeout: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator to cache API view responses

    Args:
        timeout: Cache timeout in seconds (uses settings default if None)
        key_func: Function to generate cache key from request args

    Usage:
        @cache_response(timeout=300, key_func=lambda req, *args, **kwargs: f"view:{req.path}")
        def get(self, request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(view_instance, request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                # Default key based on path and query params
                query_string = request.META.get('QUERY_STRING', '')
                path = request.path
                cache_key = hashlib.md5(f"{path}?{query_string}".encode()).hexdigest()

            # Try to get from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return Response(cached_data)

            # Execute view function
            logger.debug(f"Cache MISS for key: {cache_key}")
            response = view_func(view_instance, request, *args, **kwargs)

            # Cache successful responses
            if isinstance(response, Response) and response.status_code == 200:
                ttl = timeout or settings.CACHE_TTL.get('MEDIUM', 300)
                cache.set(cache_key, response.data, ttl)
                logger.debug(f"Cached response for key: {cache_key} (TTL: {ttl}s)")

            return response
        return wrapper
    return decorator


def cache_queryset(timeout: Optional[int] = None, cache_key: Optional[str] = None):
    """
    Decorator to cache queryset results

    Args:
        timeout: Cache timeout in seconds
        cache_key: Cache key (will auto-generate if None)

    Usage:
        @cache_queryset(timeout=600, cache_key="all_problems")
        def get_all_problems():
            return Problem.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_key
            if not key:
                func_name = func.__name__
                key_parts = [str(arg) for arg in args] + [f"{k}:{v}" for k, v in kwargs.items()]
                key = f"qs:{func_name}:{'_'.join(key_parts)}" if key_parts else f"qs:{func_name}"

            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug(f"QuerySet cache HIT: {key}")
                return cached_result

            # Execute function
            logger.debug(f"QuerySet cache MISS: {key}")
            result = func(*args, **kwargs)

            # Cache the result
            ttl = timeout or settings.CACHE_TTL.get('MEDIUM', 300)

            # Handle QuerySet - convert to list for caching
            if isinstance(result, QuerySet):
                result_list = list(result)
                cache.set(key, result_list, ttl)
                logger.debug(f"Cached queryset: {key} (TTL: {ttl}s, count: {len(result_list)})")
                return result_list
            else:
                cache.set(key, result, ttl)
                logger.debug(f"Cached result: {key} (TTL: {ttl}s)")
                return result

        return wrapper
    return decorator


class CacheInvalidator:
    """Utility class for cache invalidation"""

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern

        Note: Pattern matching is not supported with Django's default cache backend.
        This method will simply log the pattern and return 0.
        For full pattern support, use Redis with django-redis.

        Args:
            pattern: Pattern to match (e.g., 'problem_*', 'user_stats:*')

        Returns:
            int: Number of keys deleted (always 0 with default backend)
        """
        # Pattern matching requires Redis backend which we're not using
        # Log the attempt and return gracefully
        logger.debug(f"Pattern invalidation requested for: {pattern} (not supported with current cache backend)")
        return 0

    @staticmethod
    def invalidate_problem_caches(problem_id: Optional[int] = None,
                                  platform: Optional[str] = None) -> None:
        """
        Invalidate all caches related to a problem

        Args:
            problem_id: Problem ID
            platform: Platform name (invalidates all if provided)
        """
        if problem_id:
            # Invalidate specific problem
            key = CacheKeyGenerator.problem_detail_key(problem_id=problem_id)
            cache.delete(key)
            logger.info(f"Invalidated cache for problem: {problem_id}")

        # Invalidate problem lists
        CacheInvalidator.invalidate_pattern("problem_list*")

        if platform:
            # Invalidate platform-specific caches
            CacheInvalidator.invalidate_pattern(f"problem_list*{platform}*")

    @staticmethod
    def invalidate_user_caches(user_id: int) -> None:
        """
        Invalidate all caches related to a user

        Args:
            user_id: User ID
        """
        # Invalidate user stats
        key = CacheKeyGenerator.user_stats_key(user_id)
        cache.delete(key)

        # Invalidate search history
        CacheInvalidator.invalidate_pattern(f"search_history:{user_id}*")

        logger.info(f"Invalidated caches for user: {user_id}")

    @staticmethod
    def invalidate_test_cases(problem_id: int) -> None:
        """
        Invalidate test case caches for a problem

        Args:
            problem_id: Problem ID
        """
        key = CacheKeyGenerator.test_cases_key(problem_id)
        cache.delete(key)

        # Also invalidate problem detail since it includes test cases
        problem_key = CacheKeyGenerator.problem_detail_key(problem_id=problem_id)
        cache.delete(problem_key)

        logger.info(f"Invalidated test case cache for problem: {problem_id}")


def cache_method(timeout: Optional[int] = None, key_attr: Optional[str] = None):
    """
    Decorator for caching instance methods (useful for model methods)

    Args:
        timeout: Cache timeout in seconds
        key_attr: Attribute name to use for cache key (e.g., 'id', 'pk')

    Usage:
        class Problem(models.Model):
            @cache_method(timeout=600, key_attr='id')
            def get_statistics(self):
                # Expensive computation
                return {...}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(instance, *args, **kwargs):
            # Generate cache key
            obj_id = getattr(instance, key_attr or 'pk')
            func_name = func.__name__
            cache_key = f"method:{instance.__class__.__name__}:{obj_id}:{func_name}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Method cache HIT: {cache_key}")
                return cached_result

            # Execute method
            logger.debug(f"Method cache MISS: {cache_key}")
            result = func(instance, *args, **kwargs)

            # Cache the result
            ttl = timeout or settings.CACHE_TTL.get('MEDIUM', 300)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cached method result: {cache_key} (TTL: {ttl}s)")

            return result
        return wrapper
    return decorator


def get_or_set_cache(cache_key: str, fetch_func: Callable, timeout: Optional[int] = None) -> Any:
    """
    Get value from cache or compute and set it

    Args:
        cache_key: Cache key
        fetch_func: Function to call if cache miss
        timeout: Cache timeout in seconds

    Returns:
        Cached or computed value

    Usage:
        problems = get_or_set_cache(
            'all_problems',
            lambda: Problem.objects.all(),
            timeout=600
        )
    """
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached_value

    logger.debug(f"Cache MISS: {cache_key}")
    value = fetch_func()

    ttl = timeout or settings.CACHE_TTL.get('MEDIUM', 300)
    cache.set(cache_key, value, ttl)
    logger.debug(f"Cached value: {cache_key} (TTL: {ttl}s)")

    return value


def clear_all_caches() -> None:
    """Clear all application caches (use with caution)"""
    try:
        cache.clear()
        logger.warning("All caches cleared!")
    except Exception as e:
        logger.error(f"Error clearing all caches: {e}")
