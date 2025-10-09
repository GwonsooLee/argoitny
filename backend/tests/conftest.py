"""Pytest configuration and common fixtures for AlgoItny tests"""
import os
import django

# Set Django settings module before importing any Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')

# Setup Django
django.setup()

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import Mock, patch
from api.models import User, Problem, TestCase, SearchHistory, ScriptGenerationJob
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    ProblemRepository,
    SearchHistoryRepository,
    ScriptGenerationJobRepository
)
import time


@pytest.fixture(scope='session', autouse=True)
def setup_dynamodb_tables():
    """Verify DynamoDB tables exist and clean test data (runs once per test session)"""
    client = DynamoDBClient()
    dynamodb = client.get_client()

    # Check if tables exist (don't delete them!)
    existing_tables = dynamodb.list_tables().get('TableNames', [])

    # Verify required table exists
    table_name = 'algoitny_main'
    if table_name not in existing_tables:
        raise Exception(f"Required table '{table_name}' does not exist! Please create it first.")

    print(f"Using existing table: {table_name}")

    # Clean test data from previous test runs (preserve init data like subscription plans)
    # This runs ONCE at the start of the test session
    try:
        keep_pk_prefixes = ['PLAN#']  # Subscription plans

        response = dynamodb.scan(TableName=table_name)
        items = response.get('Items', [])

        for item in items:
            pk_raw = item.get('PK', {})
            pk = pk_raw.get('S', '') if isinstance(pk_raw, dict) else str(pk_raw)

            # Keep init data (subscription plans)
            if any(pk.startswith(prefix) for prefix in keep_pk_prefixes):
                continue

            # Delete old test data
            dynamodb.delete_item(
                TableName=table_name,
                Key={'PK': item['PK'], 'SK': item['SK']}
            )

        print(f"Cleaned test data from previous runs")
    except Exception as e:
        print(f"Error cleaning old test data: {e}")

    yield

    # Don't delete tables - they should persist!


@pytest.fixture(autouse=True)
def clear_django_cache():
    """Clear Django cache after each test to avoid cached data pollution"""
    yield
    # Clear cache after test completes
    from django.core.cache import cache
    cache.clear()


@pytest.fixture
def api_client():
    """Return DRF API client"""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """Return a factory function that creates an authenticated API client for any user"""
    def _make_authenticated_client(user):
        from api.utils.jwt_helper import DynamoDBUser
        client = APIClient()
        # Wrap Django User to make it compatible with JWT token generation
        # (JWT expects email in user_id claim, not numeric ID)
        user_wrapper = DynamoDBUser({
            'user_id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture,
            'google_id': user.google_id,
            'is_active': True,
            'is_staff': False
        })
        refresh = RefreshToken.for_user(user_wrapper)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        return client
    return _make_authenticated_client


@pytest.fixture
def sample_user(db):
    """Create and return a sample user (in both Django ORM and DynamoDB)"""
    # Create in Django ORM
    user = User.objects.create_user(
        email='test@example.com',
        name='Test User',
        picture='https://example.com/picture.jpg',
        google_id='google123'
    )
    print(f"[FIXTURE] Created Django user: {user.email}, ID: {user.id}")

    # Also create in DynamoDB for authentication to work
    from api.dynamodb.repositories import UserRepository
    user_repo = UserRepository()

    # Check if user already exists in DynamoDB
    existing_user = user_repo.get_user_by_email(user.email)
    if not existing_user:
        created = user_repo.create_user({
            'user_id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture,
            'google_id': user.google_id
        })
        print(f"[FIXTURE] Created DynamoDB user: {created.get('email')}")
    else:
        print(f"[FIXTURE] DynamoDB user already exists: {existing_user.get('email')}")

    return user


@pytest.fixture
def another_user(db):
    """Create and return another user for testing (in both Django ORM and DynamoDB)"""
    # Create in Django ORM
    user = User.objects.create_user(
        email='another@example.com',
        name='Another User',
        picture='https://example.com/another.jpg',
        google_id='google456'
    )

    # Also create in DynamoDB for authentication to work
    from api.dynamodb.repositories import UserRepository
    user_repo = UserRepository()

    # Check if user already exists in DynamoDB
    existing_user = user_repo.get_user_by_email(user.email)
    if not existing_user:
        user_repo.create_user({
            'user_id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture,
            'google_id': user.google_id
        })

    return user


@pytest.fixture
def sample_problem(db):
    """Create and return a sample problem in both DynamoDB and Django ORM"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    problem_repo = ProblemRepository()
    platform = 'baekjoon'
    problem_id = f'test-{unique_id}'

    problem_data = {
        'title': 'A+B',
        'problem_url': 'https://www.acmicpc.net/problem/1000',
        'tags': ['math', 'implementation'],
        'solution_code': 'a, b = map(int, input().split())\nprint(a + b)',
        'language': 'python',
        'constraints': '1 <= a, b <= 10',
        'is_completed': True
    }

    # Create in DynamoDB
    problem_repo.create_problem(platform, problem_id, problem_data)

    # Also create in Django ORM for backward compatibility with SearchHistory
    django_problem, _ = Problem.objects.get_or_create(
        platform=platform,
        problem_id=problem_id,
        defaults={
            'title': problem_data['title'],
            'problem_url': problem_data.get('problem_url', ''),
            'tags': problem_data.get('tags', []),
            'solution_code': problem_data.get('solution_code', ''),
            'language': problem_data.get('language', ''),
            'constraints': problem_data.get('constraints', ''),
            'is_completed': problem_data.get('is_completed', False)
        }
    )

    # Add DynamoDB fields to Django object for tests that expect dict
    django_problem.dynamodb_data = {**problem_data, 'platform': platform, 'problem_id': problem_id}

    return django_problem


@pytest.fixture
def draft_problem(db):
    """Create and return a draft problem (no test cases) in both DynamoDB and Django ORM"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    problem_repo = ProblemRepository()
    platform = 'codeforces'
    problem_id = f'test-draft-{unique_id}'

    problem_data = {
        'title': 'Theatre Square',
        'problem_url': 'https://codeforces.com/problemset/problem/1/A',
        'tags': ['math'],
        'solution_code': 'import math\nn, m, a = map(int, input().split())\nprint(math.ceil(n/a) * math.ceil(m/a))',
        'language': 'python',
        'constraints': '1 <= n, m, a <= 10^9',
        'is_completed': False
    }

    # Create in DynamoDB
    problem_repo.create_problem(platform, problem_id, problem_data)

    # Also create in Django ORM for backward compatibility
    django_problem, _ = Problem.objects.get_or_create(
        platform=platform,
        problem_id=problem_id,
        defaults={
            'title': problem_data['title'],
            'problem_url': problem_data.get('problem_url', ''),
            'tags': problem_data.get('tags', []),
            'solution_code': problem_data.get('solution_code', ''),
            'language': problem_data.get('language', ''),
            'constraints': problem_data.get('constraints', ''),
            'is_completed': problem_data.get('is_completed', False)
        }
    )

    django_problem.dynamodb_data = {**problem_data, 'platform': platform, 'problem_id': problem_id}
    return django_problem


@pytest.fixture
def sample_problems(db):
    """Create and return multiple sample problems with test cases in both DynamoDB and Django ORM"""
    problem_repo = ProblemRepository()
    problems = []

    # Baekjoon problem 1 - use problem_id=1000 for search tests
    platform1, problem_id1 = 'baekjoon', '1000'
    problem1_data = {
        'title': 'A+B',
        'problem_url': 'https://www.acmicpc.net/problem/1000',
        'tags': ['math'],
        'language': 'python',
        'is_completed': True
    }
    problem_repo.create_problem(platform1, problem_id1, problem1_data)
    problem_repo.add_testcase(platform1, problem_id1, '1', '1 2', '3')
    problem_repo.add_testcase(platform1, problem_id1, '2', '5 7', '12')

    # Also create in Django ORM
    django_problem1, _ = Problem.objects.get_or_create(
        platform=platform1, problem_id=problem_id1,
        defaults={'title': problem1_data['title'], 'problem_url': problem1_data.get('problem_url', ''),
                  'tags': problem1_data.get('tags', []), 'language': problem1_data.get('language', ''),
                  'is_completed': problem1_data.get('is_completed', False)}
    )
    TestCase.objects.get_or_create(problem=django_problem1, input='1 2', defaults={'output': '3'})
    TestCase.objects.get_or_create(problem=django_problem1, input='5 7', defaults={'output': '12'})
    problems.append(django_problem1)

    # Baekjoon problem 2
    platform2, problem_id2 = 'baekjoon', '1001'
    problem2_data = {
        'title': 'A-B',
        'problem_url': 'https://www.acmicpc.net/problem/1001',
        'tags': ['math'],
        'language': 'python',
        'is_completed': True
    }
    problem_repo.create_problem(platform2, problem_id2, problem2_data)
    problem_repo.add_testcase(platform2, problem_id2, '1', '3 2', '1')
    problem_repo.add_testcase(platform2, problem_id2, '2', '10 5', '5')

    django_problem2, _ = Problem.objects.get_or_create(
        platform=platform2, problem_id=problem_id2,
        defaults={'title': problem2_data['title'], 'problem_url': problem2_data.get('problem_url', ''),
                  'tags': problem2_data.get('tags', []), 'language': problem2_data.get('language', ''),
                  'is_completed': problem2_data.get('is_completed', False)}
    )
    TestCase.objects.get_or_create(problem=django_problem2, input='3 2', defaults={'output': '1'})
    TestCase.objects.get_or_create(problem=django_problem2, input='10 5', defaults={'output': '5'})
    problems.append(django_problem2)

    # Codeforces problem
    platform3, problem_id3 = 'codeforces', '1A'
    problem3_data = {
        'title': 'Theatre Square',
        'problem_url': 'https://codeforces.com/problemset/problem/1/A',
        'tags': ['math'],
        'language': 'python',
        'is_completed': True
    }
    problem_repo.create_problem(platform3, problem_id3, problem3_data)
    problem_repo.add_testcase(platform3, problem_id3, '1', '6 6 4', '4')

    django_problem3, _ = Problem.objects.get_or_create(
        platform=platform3, problem_id=problem_id3,
        defaults={'title': problem3_data['title'], 'problem_url': problem3_data.get('problem_url', ''),
                  'tags': problem3_data.get('tags', []), 'language': problem3_data.get('language', ''),
                  'is_completed': problem3_data.get('is_completed', False)}
    )
    TestCase.objects.get_or_create(problem=django_problem3, input='6 6 4', defaults={'output': '4'})
    problems.append(django_problem3)

    return problems


@pytest.fixture
def sample_test_cases(sample_problem):
    """Create and return sample test cases for a problem in DynamoDB"""
    problem_repo = ProblemRepository()
    platform = sample_problem['platform']
    problem_id = sample_problem['problem_id']

    test_cases_data = [
        {'testcase_id': '1', 'input': '1 2', 'output': '3'},
        {'testcase_id': '2', 'input': '5 7', 'output': '12'},
        {'testcase_id': '3', 'input': '0 0', 'output': '0'},
    ]

    test_cases = []
    for tc_data in test_cases_data:
        tc = problem_repo.add_testcase(platform, problem_id, tc_data['testcase_id'], tc_data['input'], tc_data['output'])
        test_cases.append(tc)

    return test_cases


@pytest.fixture
def sample_search_history(sample_user, sample_problem):
    """Create and return sample search history in DynamoDB"""
    history_repo = SearchHistoryRepository()

    history = history_repo.create_search_history(
        email=sample_user.email,
        platform=sample_problem['platform'],
        problem_number=sample_problem['problem_id'],
        problem_title=sample_problem['title'],
        code='a, b = map(int, input().split())\nprint(a + b)',
        is_code_public=True
    )

    # Add additional fields that tests might expect
    history['language'] = 'python'
    history['result_summary'] = 'Passed'
    history['passed_count'] = 3
    history['failed_count'] = 0
    history['total_count'] = 3
    history['test_results'] = [
        {'test_case_id': 1, 'output': '3', 'passed': True, 'status': 'success'},
        {'test_case_id': 2, 'output': '12', 'passed': True, 'status': 'success'},
        {'test_case_id': 3, 'output': '0', 'passed': True, 'status': 'success'},
    ]

    return history


@pytest.fixture
def private_search_history(another_user, sample_problem):
    """Create and return private search history (another user) in DynamoDB"""
    history_repo = SearchHistoryRepository()

    history = history_repo.create_search_history(
        email=another_user.email,
        platform=sample_problem['platform'],
        problem_number=sample_problem['problem_id'],
        problem_title=sample_problem['title'],
        code='private code here',
        is_code_public=False
    )

    # Add additional fields that tests might expect
    history['language'] = 'python'
    history['result_summary'] = 'Failed'
    history['passed_count'] = 1
    history['failed_count'] = 2
    history['total_count'] = 3
    history['test_results'] = [
        {'test_case_id': 1, 'output': '3', 'passed': True, 'status': 'success'},
        {'test_case_id': 2, 'output': '11', 'passed': False, 'status': 'success'},
        {'test_case_id': 3, 'output': '1', 'passed': False, 'status': 'success'},
    ]

    return history


@pytest.fixture
def sample_script_job():
    """Create and return a sample script generation job in DynamoDB"""
    job_repo = ScriptGenerationJobRepository()

    job = job_repo.create_job(
        platform='baekjoon',
        problem_id='2000',
        title='Test Problem',
        problem_url='https://www.acmicpc.net/problem/2000',
        tags=['math'],
        solution_code='print("test")',
        language='python',
        constraints='1 <= n <= 100',
        status='PENDING'
    )

    return job


@pytest.fixture
def completed_script_job():
    """Create and return a completed script generation job in DynamoDB"""
    job_repo = ScriptGenerationJobRepository()

    job = job_repo.create_job(
        platform='baekjoon',
        problem_id='3000',
        title='Completed Job',
        problem_url='https://www.acmicpc.net/problem/3000',
        tags=['math'],
        solution_code='print("test")',
        language='python',
        constraints='1 <= n <= 100',
        status='COMPLETED'
    )

    # Update with generator_code
    job_repo.update_job(
        job_id=job['id'],
        generator_code='def generate_test_cases(n):\n    return [str(i) for i in range(n)]'
    )

    # Get updated job
    job = job_repo.get_job(job['id'])

    return job


# Mock fixtures for external services

@pytest.fixture
def mock_google_oauth():
    """Mock Google OAuth service"""
    with patch('api.views.auth.GoogleOAuthService') as mock:
        mock.verify_token.return_value = {
            'sub': 'google123',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/picture.jpg'
        }
        mock.get_or_create_user.return_value = Mock(
            id=1,
            email='test@example.com',
            name='Test User',
            picture='https://example.com/picture.jpg',
            google_id='google123'
        )
        yield mock


@pytest.fixture
def mock_gemini_service():
    """Mock Gemini AI service"""
    with patch('api.services.gemini_service.GeminiService') as mock:
        mock_instance = Mock()
        mock_instance.generate_test_case_generator_code.return_value = '''
def generate_test_cases(n):
    """Generate n test cases"""
    cases = []
    for i in range(n):
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        cases.append(f"{a} {b}")
    return cases
'''
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_judge0_service():
    """Mock Judge0 code execution service"""
    with patch('api.services.code_execution_service.CodeExecutionService.execute_with_test_cases') as mock:
        mock.return_value = [
            {'status': 'success', 'output': '3', 'input': '1 2'},
            {'status': 'success', 'output': '12', 'input': '5 7'},
            {'status': 'success', 'output': '0', 'input': '0 0'},
        ]
        yield mock


@pytest.fixture
def mock_judge0_service_failure():
    """Mock Judge0 service with failure"""
    with patch('api.services.code_execution_service.CodeExecutionService.execute_with_test_cases') as mock:
        mock.return_value = [
            {'status': 'success', 'output': '3', 'input': '1 2'},
            {'status': 'error', 'output': '', 'input': '5 7', 'error': 'Compilation error'},
            {'status': 'success', 'output': '0', 'input': '0 0'},
        ]
        yield mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution"""
    with patch('celery.result.AsyncResult') as mock:
        mock_task = Mock()
        mock_task.id = 'test-task-id-123'
        mock_task.state = 'SUCCESS'
        mock_task.result = {'status': 'COMPLETED', 'message': 'Test completed'}
        mock.return_value = mock_task
        yield mock


@pytest.fixture
def mock_celery_delay():
    """Mock Celery task.delay()"""
    with patch('api.tasks.execute_code_task.delay') as mock:
        mock_result = Mock()
        mock_result.id = 'task-123'
        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_generate_script_task():
    """Mock generate_script_task.delay()"""
    with patch('api.tasks.generate_script_task.delay') as mock:
        mock_result = Mock()
        mock_result.id = 'script-task-123'
        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_generate_outputs_task():
    """Mock generate_outputs_task.delay()"""
    with patch('api.tasks.generate_outputs_task.delay') as mock:
        mock_result = Mock()
        mock_result.id = 'output-task-123'
        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_test_case_generator():
    """Mock TestCaseGenerator.execute_generator_code()"""
    with patch('api.services.test_case_generator.TestCaseGenerator.execute_generator_code') as mock:
        mock.return_value = ['1 2', '3 4', '5 6', '7 8', '9 10']
        yield mock


# Helper fixtures

@pytest.fixture
def valid_google_token():
    """Return a valid (mocked) Google ID token"""
    return 'valid_google_token_12345'


@pytest.fixture
def invalid_google_token():
    """Return an invalid Google ID token"""
    return 'invalid_token'


@pytest.fixture
def jwt_tokens(sample_user):
    """Generate and return JWT tokens for sample user"""
    refresh = RefreshToken.for_user(sample_user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }
