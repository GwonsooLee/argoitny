"""Tests for rate limiting functionality"""
import pytest
from django.utils import timezone
from api.models import User, SubscriptionPlan, UsageLog, Problem, TestCase, SearchHistory
from api.utils.rate_limit import check_rate_limit, log_usage
from django.conf import settings


@pytest.fixture
def free_plan(db):
    """Create a Free subscription plan with limits"""
    return SubscriptionPlan.objects.create(
        name='Free',
        max_hints_per_day=5,
        max_executions_per_day=50,
        is_active=True
    )


@pytest.fixture
def unlimited_plan(db):
    """Create a plan with unlimited access"""
    return SubscriptionPlan.objects.create(
        name='Unlimited',
        max_hints_per_day=-1,
        max_executions_per_day=-1,
        is_active=True
    )


@pytest.fixture
def test_user(db, free_plan):
    """Create a user with free plan"""
    user = User.objects.create_user(
        email='test@example.com',
        name='Test User',
        google_id='test123'
    )
    user.subscription_plan = free_plan
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    admin_email = 'admin@example.com'
    settings.ADMIN_EMAILS = [admin_email]

    user = User.objects.create_user(
        email=admin_email,
        name='Admin User',
        google_id='admin123'
    )
    return user


@pytest.fixture
def sample_problem(db):
    """Create a sample problem"""
    problem = Problem.objects.create(
        platform='baekjoon',
        problem_id='1000',
        title='A+B',
        is_completed=True
    )
    TestCase.objects.create(problem=problem, input='1 2', output='3')
    return problem


@pytest.mark.django_db
class TestRateLimitUtility:
    """Test rate limiting utility functions"""

    def test_check_rate_limit_within_limit(self, test_user):
        """User within daily limit should be allowed"""
        allowed, current, limit, message = check_rate_limit(test_user, 'hint')

        assert allowed is True
        assert current == 0
        assert limit == 5
        assert 'Within limit' in message

    def test_check_rate_limit_at_limit(self, test_user):
        """User at daily limit should be denied"""
        # Create 5 usage logs for today
        for _ in range(5):
            UsageLog.objects.create(user=test_user, action='hint')

        allowed, current, limit, message = check_rate_limit(test_user, 'hint')

        assert allowed is False
        assert current == 5
        assert limit == 5
        assert 'exceeded' in message

    def test_check_rate_limit_admin_unlimited(self, admin_user):
        """Admin users should have unlimited access"""
        allowed, current, limit, message = check_rate_limit(admin_user, 'hint')

        assert allowed is True
        assert current == 0
        assert limit == -1
        assert 'unlimited' in message.lower()

    def test_check_rate_limit_unlimited_plan(self, db, unlimited_plan):
        """Users with unlimited plan should have unlimited access"""
        user = User.objects.create_user(
            email='unlimited@example.com',
            name='Unlimited User',
            google_id='unlimited123'
        )
        user.subscription_plan = unlimited_plan
        user.save()

        allowed, current, limit, message = check_rate_limit(user, 'hint')

        assert allowed is True
        assert limit == -1
        assert 'Unlimited' in message

    def test_check_rate_limit_invalid_action(self, test_user):
        """Invalid action should return error"""
        allowed, current, limit, message = check_rate_limit(test_user, 'invalid_action')

        assert allowed is False
        assert 'Invalid action' in message

    def test_log_usage_creates_entry(self, test_user, sample_problem):
        """log_usage should create a UsageLog entry"""
        initial_count = UsageLog.objects.filter(user=test_user).count()

        log_usage(test_user, 'hint', sample_problem, {'context': 'test'})

        new_count = UsageLog.objects.filter(user=test_user).count()
        assert new_count == initial_count + 1

        log_entry = UsageLog.objects.filter(user=test_user).first()
        assert log_entry.action == 'hint'
        assert log_entry.problem == sample_problem
        assert log_entry.metadata == {'context': 'test'}

    def test_rate_limit_execution_action(self, test_user):
        """Rate limiting should work for execution action"""
        # Create 49 executions (limit is 50)
        for _ in range(49):
            UsageLog.objects.create(user=test_user, action='execution')

        allowed, current, limit, message = check_rate_limit(test_user, 'execution')

        assert allowed is True
        assert current == 49
        assert limit == 50

        # Add one more to hit the limit
        UsageLog.objects.create(user=test_user, action='execution')

        allowed, current, limit, message = check_rate_limit(test_user, 'execution')

        assert allowed is False
        assert current == 50


@pytest.mark.django_db
class TestHintGenerationRateLimit:
    """Test rate limiting on hint generation endpoint"""

    def test_hint_generation_within_limit(self, authenticated_client, test_user, sample_problem):
        """Hint generation should succeed within daily limit"""
        # Create a search history with failures
        history = SearchHistory.objects.create(
            user=test_user,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='A+B',
            code='print("test")',
            language='python',
            result_summary='Failed',
            passed_count=0,
            failed_count=1,
            total_count=1
        )

        response = authenticated_client(test_user).post(f'/api/history/{history.id}/hints/generate/')

        assert response.status_code in [200, 202]  # Either completed or accepted

    def test_hint_generation_exceeds_limit(self, authenticated_client, test_user, sample_problem):
        """Hint generation should fail when limit exceeded"""
        # Create 5 hint usages (at the limit)
        for _ in range(5):
            UsageLog.objects.create(user=test_user, action='hint')

        # Create a search history
        history = SearchHistory.objects.create(
            user=test_user,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='A+B',
            code='print("test")',
            language='python',
            result_summary='Failed',
            passed_count=0,
            failed_count=1,
            total_count=1
        )

        response = authenticated_client(test_user).post(f'/api/history/{history.id}/hints/generate/')

        assert response.status_code == 429  # Too Many Requests
        assert 'error' in response.data
        assert 'limit' in response.data


@pytest.mark.django_db
class TestExecutionRateLimit:
    """Test rate limiting on code execution endpoint"""

    def test_execution_within_limit(self, authenticated_client, test_user, sample_problem):
        """Code execution should succeed within daily limit"""
        response = authenticated_client(test_user).post('/api/execute/', {
            'code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'problem_id': sample_problem.id,
            'is_code_public': False
        })

        assert response.status_code == 202  # Accepted

    def test_execution_exceeds_limit(self, authenticated_client, test_user, sample_problem):
        """Code execution should fail when limit exceeded"""
        # Create 50 execution usages (at the limit)
        for _ in range(50):
            UsageLog.objects.create(user=test_user, action='execution')

        response = authenticated_client(test_user).post('/api/execute/', {
            'code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'problem_id': sample_problem.id,
            'is_code_public': False
        })

        assert response.status_code == 429  # Too Many Requests
        assert 'error' in response.data
        assert 'limit' in response.data

    def test_admin_no_execution_limit(self, authenticated_client, admin_user, sample_problem):
        """Admin users should not be subject to execution limits"""
        # Create 100 execution usages (would exceed normal limits)
        for _ in range(100):
            UsageLog.objects.create(user=admin_user, action='execution')

        response = authenticated_client(admin_user).post('/api/execute/', {
            'code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'problem_id': sample_problem.id,
            'is_code_public': False
        })

        assert response.status_code == 202  # Should still be accepted


@pytest.mark.django_db
class TestPermissions:
    """Test admin-only permissions"""

    def test_problem_list_requires_permission(self, authenticated_client, db, sample_problem):
        """Problem list should check can_view_all_problems permission"""
        # Create user without permission
        no_view_plan = SubscriptionPlan.objects.create(
            name='No View',
            can_view_all_problems=False,
            max_hints_per_day=5,
            max_executions_per_day=50
        )
        user = User.objects.create_user(
            email='noview@example.com',
            name='No View User',
            google_id='noview123'
        )
        user.subscription_plan = no_view_plan
        user.save()

        response = authenticated_client(user).get('/api/problems/')

        assert response.status_code == 403

    def test_problem_registration_requires_permission(self, authenticated_client, db):
        """Problem registration should check can_register_problems permission"""
        # Create user without permission
        no_register_plan = SubscriptionPlan.objects.create(
            name='No Register',
            can_register_problems=False,
            max_hints_per_day=5,
            max_executions_per_day=50
        )
        user = User.objects.create_user(
            email='noreg@example.com',
            name='No Register User',
            google_id='noreg123'
        )
        user.subscription_plan = no_register_plan
        user.save()

        response = authenticated_client(user).post('/api/register/generate-test-cases/', {
            'platform': 'baekjoon',
            'problem_id': '1000',
            'title': 'Test',
            'language': 'python',
            'constraints': '1 <= n <= 100'
        })

        assert response.status_code == 403
