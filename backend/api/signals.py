"""
Django signals for cache invalidation and user management

This module contains signal handlers that automatically invalidate caches
when models are created, updated, or deleted, and manage user subscription plans.
"""
import logging
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings

from .models import Problem, TestCase, SearchHistory, User, SubscriptionPlan
from .utils.cache import CacheInvalidator

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Problem)
def invalidate_problem_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate problem-related caches when a problem is created or updated

    Args:
        sender: Model class
        instance: Problem instance
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal parameters
    """
    try:
        # Invalidate problem detail cache
        CacheInvalidator.invalidate_problem_caches(
            problem_id=instance.id,
            platform=instance.platform
        )

        # Log the action
        action = "created" if created else "updated"
        logger.info(f"Problem {action}: {instance.id}. Invalidated related caches.")

    except Exception as e:
        logger.error(f"Error invalidating cache on problem save: {e}")


@receiver(post_delete, sender=Problem)
def invalidate_problem_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate problem-related caches when a problem is deleted

    Args:
        sender: Model class
        instance: Problem instance
        **kwargs: Additional signal parameters
    """
    try:
        # Invalidate problem caches
        CacheInvalidator.invalidate_problem_caches(
            problem_id=instance.id,
            platform=instance.platform
        )

        logger.info(f"Problem deleted: {instance.id}. Invalidated related caches.")

    except Exception as e:
        logger.error(f"Error invalidating cache on problem delete: {e}")


@receiver(post_save, sender=TestCase)
def invalidate_test_case_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate test case caches when a test case is created or updated

    Args:
        sender: Model class
        instance: TestCase instance
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal parameters
    """
    try:
        # Invalidate test case and problem detail caches
        CacheInvalidator.invalidate_test_cases(instance.problem_id)

        # Also invalidate problem list caches since test_case_count might change
        CacheInvalidator.invalidate_problem_caches(
            problem_id=instance.problem_id,
            platform=instance.problem.platform
        )

        action = "created" if created else "updated"
        logger.info(f"TestCase {action} for problem {instance.problem_id}. Invalidated caches.")

    except Exception as e:
        logger.error(f"Error invalidating cache on test case save: {e}")


@receiver(post_delete, sender=TestCase)
def invalidate_test_case_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate test case caches when a test case is deleted

    Args:
        sender: Model class
        instance: TestCase instance
        **kwargs: Additional signal parameters
    """
    try:
        # Invalidate test case and problem caches
        CacheInvalidator.invalidate_test_cases(instance.problem_id)

        # Also invalidate problem list caches
        CacheInvalidator.invalidate_problem_caches(
            problem_id=instance.problem_id
        )

        logger.info(f"TestCase deleted for problem {instance.problem_id}. Invalidated caches.")

    except Exception as e:
        logger.error(f"Error invalidating cache on test case delete: {e}")


@receiver(post_save, sender=SearchHistory)
def invalidate_user_cache_on_history_save(sender, instance, created, **kwargs):
    """
    Invalidate user-related caches when search history is created

    Args:
        sender: Model class
        instance: SearchHistory instance
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal parameters
    """
    try:
        # Only invalidate on creation or when is_code_public changes
        if created or 'is_code_public' in getattr(instance, '_dirty_fields', set()):
            # Invalidate user stats cache
            if instance.user_id:
                CacheInvalidator.invalidate_user_caches(instance.user_id)

            # Invalidate search history caches
            CacheInvalidator.invalidate_pattern(f"search_history*")

            action = "created" if created else "updated"
            logger.info(f"SearchHistory {action}. Invalidated user caches.")

    except Exception as e:
        logger.error(f"Error invalidating cache on search history save: {e}")


@receiver(post_save, sender=User)
def assign_admin_plan_to_admin_users(sender, instance, **kwargs):
    """
    Automatically assign Admin plan to users with admin email

    Args:
        sender: Model class
        instance: User instance
        **kwargs: Additional signal parameters
    """
    try:
        # Check if user is admin
        is_admin_user = instance.email in settings.ADMIN_EMAILS

        # If user is admin and doesn't have Admin plan, assign it
        if is_admin_user:
            admin_plan = SubscriptionPlan.objects.filter(name='Admin', is_active=True).first()

            if admin_plan and instance.subscription_plan != admin_plan:
                instance.subscription_plan = admin_plan
                # Prevent recursive save by using update
                User.objects.filter(pk=instance.pk).update(subscription_plan=admin_plan)
                logger.info(f"Assigned Admin plan to admin user: {instance.email}")

    except Exception as e:
        logger.error(f"Error assigning admin plan: {e}")
