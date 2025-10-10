#!/usr/bin/env python3
"""Check existing plans in DynamoDB"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories.subscription_plan_repository import SubscriptionPlanRepository

def main():
    """Check existing plans"""
    print("=" * 60)
    print("Existing Subscription Plans in DynamoDB")
    print("=" * 60)

    table = DynamoDBClient.get_table()
    plan_repo = SubscriptionPlanRepository(table)

    # Get all plans
    plans = plan_repo.list_plans()

    if not plans:
        print("No plans found in database")
        return

    for plan in plans:
        print(f"\nPlan ID: {plan['id']}")
        print(f"  Name: {plan['name']}")
        print(f"  Description: {plan['description']}")
        print(f"  Max hints/day: {plan['max_hints_per_day']}")
        print(f"  Max executions/day: {plan['max_executions_per_day']}")
        print(f"  Is active: {plan['is_active']}")

    print("\n" + "=" * 60)
    print(f"Total plans: {len(plans)}")
    print("=" * 60)

if __name__ == '__main__':
    main()
