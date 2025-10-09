#!/usr/bin/env python3
"""
Show detailed information about remaining items.
"""

import os
import sys
import django
import json

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.dynamodb.repositories.user_repository import UserRepository
from api.dynamodb.repositories.subscription_plan_repository import SubscriptionPlanRepository


def show_details():
    """Show detailed information about remaining items."""
    print("="*80)
    print("DETAILED VIEW: Remaining Items After Cleanup")
    print("="*80)

    # Show subscription plans
    plan_repo = SubscriptionPlanRepository()
    plans = plan_repo.list_plans()

    print(f"\nSUBSCRIPTION PLANS ({len(plans)} items):")
    print("-"*80)
    for plan in plans:
        print(f"\nPlan ID: {plan['id']}")
        print(f"  Name: {plan['name']}")
        print(f"  Description: {plan.get('description', 'N/A')}")
        print(f"  Max Hints/Day: {plan['max_hints_per_day']}")
        print(f"  Max Executions/Day: {plan['max_executions_per_day']}")
        print(f"  Max Problems: {plan.get('max_problems', -1)}")
        print(f"  Price: ${plan.get('price', 0)}")
        print(f"  Active: {plan.get('is_active', True)}")

    # Show users
    user_repo = UserRepository()
    users = user_repo.list_users()

    print(f"\n\nUSERS ({len(users)} items):")
    print("-"*80)
    for user in users:
        print(f"\nUser ID: {user['user_id']}")
        print(f"  Email: {user['email']}")
        print(f"  Name: {user.get('name', 'N/A')}")
        print(f"  Google ID: {user.get('google_id', 'N/A')}")
        print(f"  Subscription Plan ID: {user.get('subscription_plan_id', 'N/A')}")
        print(f"  Active: {user.get('is_active', True)}")
        print(f"  Staff: {user.get('is_staff', False)}")

    print("\n" + "="*80)
    print("Summary:")
    print(f"  - Total Subscription Plans: {len(plans)}")
    print(f"  - Total Users: {len(users)}")
    print(f"  - Total Items Remaining: {len(plans) + len(users)}")
    print("="*80)


if __name__ == '__main__':
    show_details()
