#!/usr/bin/env python
"""Initialize database with migrations and default data"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import execute_from_command_line
from api.models import SubscriptionPlan

def run_migrations():
    """Run database migrations"""
    print("Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("✅ Migrations completed successfully")

def create_default_plan():
    """Create default subscription plan if it doesn't exist"""
    try:
        plan, created = SubscriptionPlan.objects.get_or_create(
            name='Free',
            defaults={
                'description': 'Free plan with basic features',
                'max_hints_per_day': 5,
                'max_executions_per_day': 50,
                'max_problems': -1,  # Unlimited problems
                'can_view_all_problems': True,
                'can_register_problems': False,
                'is_active': True,
            }
        )

        if created:
            print("✅ Default subscription plan 'Free' created successfully")
        else:
            print("✅ Default subscription plan 'Free' already exists")

    except Exception as e:
        print(f"⚠️ Error creating default plan: {e}")
        # Non-fatal error, continue

def main():
    """Main initialization function"""
    print("========================================")
    print("Initializing AlgoItny Database")
    print("========================================")

    # Run migrations
    run_migrations()

    # Create default data
    create_default_plan()

    print("========================================")
    print("✅ Database initialization complete")
    print("========================================")

if __name__ == '__main__':
    main()