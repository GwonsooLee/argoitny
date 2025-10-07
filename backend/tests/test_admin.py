"""Tests for admin views"""
import pytest
from django.urls import reverse
from rest_framework import status
from api.models import User, SubscriptionPlan, UsageLog, Problem
from django.conf import settings


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    # Add the user's email to ADMIN_EMAILS temporarily
    admin_email = 'admin@example.com'
    settings.ADMIN_EMAILS = [admin_email]

    user = User.objects.create_user(
        email=admin_email,
        name='Admin User',
        google_id='admin123'
    )
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular (non-admin) user"""
    user = User.objects.create_user(
        email='user@example.com',
        name='Regular User',
        google_id='user123'
    )
    return user


@pytest.fixture
def free_plan(db):
    """Create a Free subscription plan"""
    return SubscriptionPlan.objects.create(
        name='Free',
        description='Free plan with limited features',
        max_hints_per_day=5,
        max_executions_per_day=50,
        max_problems=-1,
        can_view_all_problems=True,
        can_register_problems=False,
        is_active=True
    )


@pytest.fixture
def pro_plan(db):
    """Create a Pro subscription plan"""
    return SubscriptionPlan.objects.create(
        name='Pro',
        description='Pro plan with more features',
        max_hints_per_day=50,
        max_executions_per_day=500,
        max_problems=-1,
        can_view_all_problems=True,
        can_register_problems=False,
        is_active=True
    )


@pytest.mark.django_db
class TestUserManagementView:
    """Test user management admin endpoint"""

    def test_list_users_as_admin(self, authenticated_client, admin_user, regular_user, free_plan):
        """Admin can list all users"""
        # Assign subscription plan to regular user
        regular_user.subscription_plan = free_plan
        regular_user.save()

        response = authenticated_client(admin_user).get('/api/admin/users/')

        assert response.status_code == status.HTTP_200_OK
        assert 'users' in response.data
        assert len(response.data['users']) >= 2  # At least admin and regular user

    def test_list_users_as_non_admin(self, authenticated_client, regular_user):
        """Non-admin cannot list users"""
        response = authenticated_client(regular_user).get('/api/admin/users/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data

    def test_filter_users_by_plan(self, authenticated_client, admin_user, regular_user, free_plan, pro_plan):
        """Admin can filter users by subscription plan"""
        regular_user.subscription_plan = free_plan
        regular_user.save()

        response = authenticated_client(admin_user).get(f'/api/admin/users/?plan_id={free_plan.id}')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['users']) >= 1
        # Check that returned users have the correct plan
        for user_data in response.data['users']:
            if user_data['subscription_plan']:
                assert user_data['subscription_plan'] == free_plan.id

    def test_search_users_by_email(self, authenticated_client, admin_user, regular_user):
        """Admin can search users by email"""
        response = authenticated_client(admin_user).get('/api/admin/users/?search=user@example.com')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['users']) >= 1
        assert any(u['email'] == 'user@example.com' for u in response.data['users'])

    def test_update_user_subscription_plan(self, authenticated_client, admin_user, regular_user, free_plan, pro_plan):
        """Admin can update user's subscription plan"""
        response = authenticated_client(admin_user).patch(
            f'/api/admin/users/{regular_user.id}/',
            {'subscription_plan': pro_plan.id}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['subscription_plan'] == pro_plan.id

        # Verify in database
        regular_user.refresh_from_db()
        assert regular_user.subscription_plan == pro_plan

    def test_update_user_as_non_admin(self, authenticated_client, regular_user, free_plan):
        """Non-admin cannot update user subscription plan"""
        response = authenticated_client(regular_user).patch(
            f'/api/admin/users/{regular_user.id}/',
            {'subscription_plan': free_plan.id}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSubscriptionPlanManagementView:
    """Test subscription plan management admin endpoint"""

    def test_list_plans_as_admin(self, authenticated_client, admin_user, free_plan, pro_plan):
        """Admin can list all subscription plans"""
        response = authenticated_client(admin_user).get('/api/admin/plans/')

        assert response.status_code == status.HTTP_200_OK
        assert 'plans' in response.data
        assert len(response.data['plans']) >= 2

    def test_list_plans_as_non_admin(self, authenticated_client, regular_user):
        """Non-admin cannot list plans"""
        response = authenticated_client(regular_user).get('/api/admin/plans/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_specific_plan(self, authenticated_client, admin_user, free_plan):
        """Admin can get a specific plan"""
        response = authenticated_client(admin_user).get(f'/api/admin/plans/{free_plan.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == free_plan.id
        assert response.data['name'] == 'Free'

    def test_create_plan_as_admin(self, authenticated_client, admin_user):
        """Admin can create a new subscription plan"""
        plan_data = {
            'name': 'Enterprise',
            'description': 'Enterprise plan with unlimited features',
            'max_hints_per_day': -1,
            'max_executions_per_day': -1,
            'max_problems': -1,
            'can_view_all_problems': True,
            'can_register_problems': True,
            'is_active': True
        }

        response = authenticated_client(admin_user).post('/api/admin/plans/', plan_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Enterprise'
        assert response.data['max_hints_per_day'] == -1

    def test_create_plan_as_non_admin(self, authenticated_client, regular_user):
        """Non-admin cannot create plans"""
        plan_data = {
            'name': 'Test Plan',
            'max_hints_per_day': 10,
            'max_executions_per_day': 100
        }

        response = authenticated_client(regular_user).post('/api/admin/plans/', plan_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_plan_as_admin(self, authenticated_client, admin_user, free_plan):
        """Admin can update a subscription plan"""
        response = authenticated_client(admin_user).patch(
            f'/api/admin/plans/{free_plan.id}/',
            {'max_hints_per_day': 10}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['max_hints_per_day'] == 10

        # Verify in database
        free_plan.refresh_from_db()
        assert free_plan.max_hints_per_day == 10

    def test_delete_plan_without_users(self, authenticated_client, admin_user):
        """Admin can delete a plan with no users"""
        plan = SubscriptionPlan.objects.create(
            name='Temporary',
            max_hints_per_day=5,
            max_executions_per_day=50
        )

        response = authenticated_client(admin_user).delete(f'/api/admin/plans/{plan.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SubscriptionPlan.objects.filter(id=plan.id).exists()

    def test_delete_plan_with_users(self, authenticated_client, admin_user, regular_user, free_plan):
        """Admin cannot delete a plan with active users"""
        regular_user.subscription_plan = free_plan
        regular_user.save()

        response = authenticated_client(admin_user).delete(f'/api/admin/plans/{free_plan.id}/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert SubscriptionPlan.objects.filter(id=free_plan.id).exists()


@pytest.mark.django_db
class TestUsageStatsView:
    """Test usage statistics admin endpoint"""

    def test_get_usage_stats_as_admin(self, authenticated_client, admin_user, regular_user):
        """Admin can view usage statistics"""
        # Create some usage logs
        UsageLog.objects.create(user=regular_user, action='hint')
        UsageLog.objects.create(user=regular_user, action='execution')

        response = authenticated_client(admin_user).get('/api/admin/usage-stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_users' in response.data
        assert 'total_problems' in response.data
        assert 'hints_count' in response.data
        assert 'executions_count' in response.data
        assert 'top_users' in response.data
        assert 'plan_distribution' in response.data

    def test_get_usage_stats_as_non_admin(self, authenticated_client, regular_user):
        """Non-admin cannot view usage statistics"""
        response = authenticated_client(regular_user).get('/api/admin/usage-stats/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_usage_stats_with_date_range(self, authenticated_client, admin_user):
        """Admin can get usage stats for different date ranges"""
        response = authenticated_client(admin_user).get('/api/admin/usage-stats/?days=30')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['period_days'] == 30
