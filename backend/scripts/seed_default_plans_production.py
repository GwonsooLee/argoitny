#!/usr/bin/env python3
"""
Seed default subscription plans to Production DynamoDB

IMPORTANT: This script targets PRODUCTION database!

Safety features:
- Dry-run mode by default
- Confirmation required for actual execution
- Only creates plans that don't exist (no overwrites)

Usage:
  # Dry run (safe, no changes)
  python seed_default_plans_production.py --dry-run

  # Actual seed (requires confirmation)
  python seed_default_plans_production.py --execute
"""
import os
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# IMPORTANT: Ensure we're NOT using LocalStack
if 'LOCALSTACK_URL' in os.environ:
    del os.environ['LOCALSTACK_URL']

# Set AWS region
os.environ.setdefault('AWS_DEFAULT_REGION', 'ap-northeast-2')

from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories.base_repository import BaseRepository


class SubscriptionPlanRepository(BaseRepository):
    """Repository for SubscriptionPlan entity"""

    def create_plan(self, plan_id, plan_data):
        """Create a subscription plan"""
        import time

        # Convert to DynamoDB item with short field names (NEW STRUCTURE)
        item = {
            'PK': 'PLAN',
            'SK': f'META#{plan_id}',
            'tp': 'plan',
            'dat': {
                'nm': plan_data['name'],
                'dsc': plan_data.get('description', ''),
                'mh': plan_data.get('max_hints_per_day', 5),
                'me': plan_data.get('max_executions_per_day', 50),
                'mp': plan_data.get('max_problems', -1),
                'cva': plan_data.get('can_view_all_problems', True),
                'crp': plan_data.get('can_register_problems', False),
                'act': plan_data.get('is_active', True),
            },
            'crt': int(time.time()),
            'upd': int(time.time()),
        }

        self.put_item(item)
        return self._from_item_to_plan(item)

    def get_plan(self, plan_id):
        """Get plan by ID"""
        item = self.get_item('PLAN', f'META#{plan_id}')
        if not item:
            return None
        return self._from_item_to_plan(item)

    def plan_exists(self, plan_id):
        """Check if plan exists"""
        return self.get_plan(plan_id) is not None

    def _from_item_to_plan(self, item):
        """Convert DynamoDB item to plan dict with long field names"""
        if not item or 'dat' not in item:
            return None

        dat = item['dat']
        plan_id = item['SK'].replace('META#', '')

        return {
            'id': int(plan_id),
            'name': dat.get('nm', ''),
            'description': dat.get('dsc', ''),
            'max_hints_per_day': dat.get('mh', 5),
            'max_executions_per_day': dat.get('me', 50),
            'max_problems': dat.get('mp', -1),
            'can_view_all_problems': dat.get('cva', True),
            'can_register_problems': dat.get('crp', False),
            'is_active': dat.get('act', True),
            'created_at': item.get('crt', 0),
            'updated_at': item.get('upd', 0),
        }


def seed_default_plans(dry_run=True):
    """Seed default Free, Pro, and Admin plans"""
    print("=" * 70)
    print("SEED DEFAULT SUBSCRIPTION PLANS - PRODUCTION")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'EXECUTE (will modify data)'}")
    print(f"AWS Region: {os.environ.get('AWS_DEFAULT_REGION', 'Not set')}")
    print(f"Table: algoitny_main")
    print("=" * 70)
    print()

    if not dry_run:
        print("⚠️  WARNING: This will modify PRODUCTION DynamoDB!")
        confirm = input("Type 'SEED' to continue: ")
        if confirm != 'SEED':
            print("❌ Cancelled by user")
            return 0, 0

    # Initialize repository
    table = DynamoDBClient.get_table()
    plan_repo = SubscriptionPlanRepository(table)

    # Default plans
    plans = [
        {
            'id': 1,
            'name': 'Free',
            'description': 'Free plan with limited features',
            'max_hints_per_day': 5,
            'max_executions_per_day': 50,
            'max_problems': -1,  # Unlimited
            'can_view_all_problems': True,
            'can_register_problems': False,
            'is_active': True,
        },
        {
            'id': 2,
            'name': 'Pro',
            'description': 'Pro plan with enhanced features',
            'max_hints_per_day': 30,
            'max_executions_per_day': 200,
            'max_problems': -1,  # Unlimited
            'can_view_all_problems': True,
            'can_register_problems': False,
            'is_active': True,
        },
        {
            'id': 3,
            'name': 'Admin',
            'description': 'Full access plan for administrators',
            'max_hints_per_day': -1,  # Unlimited
            'max_executions_per_day': -1,  # Unlimited
            'max_problems': -1,  # Unlimited
            'can_view_all_problems': True,
            'can_register_problems': True,
            'is_active': True,
        },
    ]

    created_count = 0
    skipped_count = 0

    for plan_data in plans:
        plan_id = plan_data['id']
        plan_name = plan_data['name']

        # Check if plan already exists
        if plan_repo.plan_exists(plan_id):
            print(f"⏭️  Skipping '{plan_name}' (ID: {plan_id}) - already exists")
            skipped_count += 1
            continue

        # Create plan
        if dry_run:
            print(f"[DRY RUN] Would create '{plan_name}' plan (ID: {plan_id})")
            print(f"   - Max hints/day: {plan_data['max_hints_per_day']}")
            print(f"   - Max executions/day: {plan_data['max_executions_per_day']}")
            print(f"   - Can register problems: {plan_data['can_register_problems']}")
        else:
            try:
                created_plan = plan_repo.create_plan(plan_id, plan_data)
                print(f"✅ Created '{plan_name}' plan (ID: {plan_id})")
                print(f"   - Max hints/day: {created_plan['max_hints_per_day']}")
                print(f"   - Max executions/day: {created_plan['max_executions_per_day']}")
                print(f"   - Can register problems: {created_plan['can_register_problems']}")
                created_count += 1
            except Exception as e:
                print(f"❌ Failed to create '{plan_name}' plan: {e}")
                import traceback
                traceback.print_exc()

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    if dry_run:
        print(f"Would create: {len([p for p in plans if not plan_repo.plan_exists(p['id'])])} plans")
        print(f"Already exist: {len([p for p in plans if plan_repo.plan_exists(p['id'])])} plans")
    else:
        print(f"Created: {created_count} plans")
        print(f"Skipped: {skipped_count} plans (already exist)")
    print("=" * 70)

    return created_count, skipped_count


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Seed Default Plans - PRODUCTION')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Dry run mode (default, no changes)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute actual seeding')

    args = parser.parse_args()
    dry_run = not args.execute

    try:
        created, skipped = seed_default_plans(dry_run=dry_run)

        if dry_run:
            print("\n✓ Dry run completed successfully!")
            print("Run with --execute to perform actual seeding")
        elif created > 0:
            print("\n✅ Default plans seeded successfully!")
        elif skipped > 0:
            print("\n✓ Default plans already exist")
        else:
            print("\n⚠️  No plans were created")

        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Failed to seed default plans: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
