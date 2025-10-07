"""Pytest configuration and common fixtures for AlgoItny tests"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import Mock, patch
from api.models import User, Problem, TestCase, SearchHistory, ScriptGenerationJob


@pytest.fixture
def api_client():
    """Return DRF API client"""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """Return a factory function that creates an authenticated API client for any user"""
    def _make_authenticated_client(user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        return client
    return _make_authenticated_client


@pytest.fixture
def sample_user(db):
    """Create and return a sample user"""
    user = User.objects.create_user(
        email='test@example.com',
        name='Test User',
        picture='https://example.com/picture.jpg',
        google_id='google123'
    )
    return user


@pytest.fixture
def another_user(db):
    """Create and return another user for testing"""
    user = User.objects.create_user(
        email='another@example.com',
        name='Another User',
        picture='https://example.com/another.jpg',
        google_id='google456'
    )
    return user


@pytest.fixture
def sample_problem(db):
    """Create and return a sample problem"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    problem, _ = Problem.objects.get_or_create(
        platform='baekjoon',
        problem_id=f'test-{unique_id}',
        defaults={
            'title':'A+B',
            'problem_url':'https://www.acmicpc.net/problem/1000',
            'tags':['math', 'implementation'],
            'solution_code':'YSwgYiA9IG1hcChpbnQsIGlucHV0KCkuc3BsaXQoKSlcbnByaW50KGEgKyBiKQ==',
            'language':'python',
            'constraints':'1 <= a, b <= 10',
            'is_completed':True
        }
    )
    return problem


@pytest.fixture
def draft_problem(db):
    """Create and return a draft problem (no test cases)"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    problem, _ = Problem.objects.get_or_create(
        platform='codeforces',
        problem_id=f'test-draft-{unique_id}',
        defaults={
            'title':'Theatre Square',
            'problem_url':'https://codeforces.com/problemset/problem/1/A',
            'tags':['math'],
            'solution_code':'aW1wb3J0IG1hdGgKbiwgbSwgYSA9IG1hcChpbnQsIGlucHV0KCkuc3BsaXQoKSkKcHJpbnQobWF0aC5jZWlsKG4vYSkgKiBtYXRoLmNlaWwobS9hKSk=',
            'language':'python',
            'constraints':'1 <= n, m, a <= 10^9',
            'is_completed':False
        }
    )
    return problem


@pytest.fixture
def sample_problems(db):
    """Create and return multiple sample problems with test cases"""
    import uuid
    problems = []

    # Baekjoon problem 1 - use problem_id=1000 for search tests
    problem1, _ = Problem.objects.get_or_create(
        platform='baekjoon',
        problem_id='1000',
        defaults={
            'title':'A+B',
            'problem_url':'https://www.acmicpc.net/problem/1000',
            'tags':['math'],
            'language':'python',
            'is_completed':True
        }
    )
    TestCase.objects.get_or_create(problem=problem1, input='1 2', defaults={'output':'3'})
    TestCase.objects.get_or_create(problem=problem1, input='5 7', defaults={'output':'12'})
    problems.append(problem1)

    # Baekjoon problem 2
    problem2, _ = Problem.objects.get_or_create(
        platform='baekjoon',
        problem_id='1001',
        defaults={
            'title':'A-B',
            'problem_url':'https://www.acmicpc.net/problem/1001',
            'tags':['math'],
            'language':'python',
            'is_completed':True
        }
    )
    TestCase.objects.get_or_create(problem=problem2, input='3 2', defaults={'output':'1'})
    TestCase.objects.get_or_create(problem=problem2, input='10 5', defaults={'output':'5'})
    problems.append(problem2)

    # Codeforces problem
    problem3, _ = Problem.objects.get_or_create(
        platform='codeforces',
        problem_id='1A',
        defaults={
            'title':'Theatre Square',
            'problem_url':'https://codeforces.com/problemset/problem/1/A',
            'tags':['math'],
            'language':'python',
            'is_completed':True
        }
    )
    TestCase.objects.get_or_create(problem=problem3, input='6 6 4', defaults={'output':'4'})
    problems.append(problem3)

    return problems


@pytest.fixture
def sample_test_cases(db, sample_problem):
    """Create and return sample test cases for a problem"""
    test_cases = [
        TestCase.objects.create(
            problem=sample_problem,
            input='1 2',
            output='3'
        ),
        TestCase.objects.create(
            problem=sample_problem,
            input='5 7',
            output='12'
        ),
        TestCase.objects.create(
            problem=sample_problem,
            input='0 0',
            output='0'
        ),
    ]
    return test_cases


@pytest.fixture
def sample_search_history(db, sample_user, sample_problem):
    """Create and return sample search history"""
    history = SearchHistory.objects.create(
        user=sample_user,
        user_identifier=sample_user.email,
        problem=sample_problem,
        platform=sample_problem.platform,
        problem_number=sample_problem.problem_id,
        problem_title=sample_problem.title,
        language='python',
        code='a, b = map(int, input().split())\nprint(a + b)',
        result_summary='Passed',
        passed_count=3,
        failed_count=0,
        total_count=3,
        is_code_public=True,
        test_results=[
            {'test_case_id': 1, 'output': '3', 'passed': True, 'status': 'success'},
            {'test_case_id': 2, 'output': '12', 'passed': True, 'status': 'success'},
            {'test_case_id': 3, 'output': '0', 'passed': True, 'status': 'success'},
        ]
    )
    return history


@pytest.fixture
def private_search_history(db, another_user, sample_problem):
    """Create and return private search history (another user)"""
    history = SearchHistory.objects.create(
        user=another_user,
        user_identifier=another_user.email,
        problem=sample_problem,
        platform=sample_problem.platform,
        problem_number=sample_problem.problem_id,
        problem_title=sample_problem.title,
        language='python',
        code='private code here',
        result_summary='Failed',
        passed_count=1,
        failed_count=2,
        total_count=3,
        is_code_public=False,
        test_results=[
            {'test_case_id': 1, 'output': '3', 'passed': True, 'status': 'success'},
            {'test_case_id': 2, 'output': '11', 'passed': False, 'status': 'success'},
            {'test_case_id': 3, 'output': '1', 'passed': False, 'status': 'success'},
        ]
    )
    return history


@pytest.fixture
def sample_script_job(db):
    """Create and return a sample script generation job"""
    job = ScriptGenerationJob.objects.create(
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
def completed_script_job(db):
    """Create and return a completed script generation job"""
    job = ScriptGenerationJob.objects.create(
        platform='baekjoon',
        problem_id='3000',
        title='Completed Job',
        problem_url='https://www.acmicpc.net/problem/3000',
        tags=['math'],
        solution_code='print("test")',
        language='python',
        constraints='1 <= n <= 100',
        status='COMPLETED',
        generator_code='def generate_test_cases(n):\n    return [str(i) for i in range(n)]'
    )
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
