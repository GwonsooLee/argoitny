#!/usr/bin/env python
"""Create default subscription plans"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import SubscriptionPlan

# Create Free plan
free_plan, created = SubscriptionPlan.objects.get_or_create(
    name='Free',
    defaults={
        'description': 'Free plan with limited features',
        'max_hints_per_day': 5,
        'max_executions_per_day': 50,
        'max_problems': -1,
        'can_view_all_problems': True,
        'can_register_problems': False,
    }
)
if created:
    print(f'✓ Created Free plan')
else:
    print(f'✓ Free plan already exists')

# Create Pro plan
pro_plan, created = SubscriptionPlan.objects.get_or_create(
    name='Pro',
    defaults={
        'description': 'Pro plan with unlimited features',
        'max_hints_per_day': 50,
        'max_executions_per_day': 500,
        'max_problems': -1,
        'can_view_all_problems': True,
        'can_register_problems': False,
    }
)
if created:
    print(f'✓ Created Pro plan')
else:
    print(f'✓ Pro plan already exists')

# Create Admin plan
admin_plan, created = SubscriptionPlan.objects.get_or_create(
    name='Admin',
    defaults={
        'description': 'Admin plan with all features',
        'max_hints_per_day': -1,  # Unlimited
        'max_executions_per_day': -1,  # Unlimited
        'max_problems': -1,
        'can_view_all_problems': True,
        'can_register_problems': True,
    }
)
if created:
    print(f'✓ Created Admin plan')
else:
    print(f'✓ Admin plan already exists')

print('\n✓ All subscription plans are ready!')
