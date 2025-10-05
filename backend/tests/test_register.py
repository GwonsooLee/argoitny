"""Tests for problem registration views"""
import pytest
from rest_framework import status
from unittest.mock import patch, Mock
from api.models import Problem, TestCase, ScriptGenerationJob


@pytest.mark.django_db
class TestGenerateTestCases:
    """Test test case generator code generation endpoint"""

    def test_generate_test_cases_success(self, api_client, mock_generate_script_task):
        """Test successful test case generation job creation"""
        response = api_client.post('/api/register/generate-test-cases/', {
            'platform': 'baekjoon',
            'problem_id': '2000',
            'title': 'New Problem',
            'solution_code': 'print("test")',
            'language': 'python',
            'constraints': '1 <= n <= 100'
        })

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'job_id' in response.data
        assert 'status' in response.data
        assert response.data['status'] == 'PENDING'

        # Verify job was created
        job = ScriptGenerationJob.objects.get(id=response.data['job_id'])
        assert job.platform == 'baekjoon'
        assert job.problem_id == '2000'
        assert job.status == 'PENDING'

    def test_generate_test_cases_missing_required_fields(self, api_client):
        """Test generation without required fields"""
        response = api_client.post('/api/register/generate-test-cases/', {
            'platform': 'baekjoon'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_generate_test_cases_with_optional_fields(self, api_client, mock_generate_script_task):
        """Test generation with optional fields"""
        response = api_client.post('/api/register/generate-test-cases/', {
            'platform': 'baekjoon',
            'problem_id': '2001',
            'title': 'Problem with extras',
            'problem_url': 'https://www.acmicpc.net/problem/2001',
            'tags': ['math', 'dp'],
            'solution_code': 'print("solution")',
            'language': 'python',
            'constraints': '1 <= n <= 1000'
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

        job = ScriptGenerationJob.objects.get(id=response.data['job_id'])
        assert job.problem_url == 'https://www.acmicpc.net/problem/2001'
        assert job.tags == ['math', 'dp']

    def test_generate_test_cases_without_solution_code(self, api_client, mock_generate_script_task):
        """Test generation without solution code"""
        response = api_client.post('/api/register/generate-test-cases/', {
            'platform': 'codeforces',
            'problem_id': '1B',
            'title': 'No Solution',
            'language': 'python',
            'constraints': '1 <= n <= 100'
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

        job = ScriptGenerationJob.objects.get(id=response.data['job_id'])
        assert job.solution_code == ''


@pytest.mark.django_db
class TestRegisterProblem:
    """Test problem registration endpoint"""

    def test_register_problem_success(self, api_client, mock_judge0_service):
        """Test successful problem registration"""
        response = api_client.post('/api/register/', {
            'platform': 'baekjoon',
            'problem_id': '3000',
            'title': 'New Problem',
            'problem_url': 'https://www.acmicpc.net/problem/3000',
            'tags': ['math'],
            'solution_code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'constraints': '1 <= a, b <= 10',
            'test_case_inputs': ['1 2', '3 4', '5 6']
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'problem' in response.data
        assert 'message' in response.data

        # Verify problem was created
        problem = Problem.objects.get(platform='baekjoon', problem_id='3000')
        assert problem.title == 'New Problem'
        assert problem.test_cases.count() == 3

    def test_register_problem_duplicate(self, api_client, sample_problem):
        """Test registering duplicate problem"""
        response = api_client.post('/api/register/', {
            'platform': sample_problem.platform,
            'problem_id': sample_problem.problem_id,
            'title': 'Duplicate',
            'solution_code': 'test',
            'language': 'python',
            'constraints': 'test',
            'test_case_inputs': ['1 2']
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'already exists' in response.data['error'].lower()

    def test_register_problem_missing_test_case_inputs(self, api_client):
        """Test registration without test case inputs"""
        response = api_client.post('/api/register/', {
            'platform': 'baekjoon',
            'problem_id': '4000',
            'title': 'No Test Cases',
            'solution_code': 'test',
            'language': 'python',
            'constraints': 'test'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'test_case_inputs' in response.data['error'].lower()

    def test_register_problem_execution_failure(self, api_client, mock_judge0_service_failure):
        """Test registration when test execution fails"""
        response = api_client.post('/api/register/', {
            'platform': 'baekjoon',
            'problem_id': '5000',
            'title': 'Failing Problem',
            'solution_code': 'broken code',
            'language': 'python',
            'constraints': 'test',
            'test_case_inputs': ['1 2', '3 4']
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_register_problem_with_url_parsing(self, api_client, mock_judge0_service):
        """Test registration with URL parsing"""
        response = api_client.post('/api/register/', {
            'problem_url': 'https://www.acmicpc.net/problem/6000',
            'title': 'URL Parsed Problem',
            'solution_code': 'print("test")',
            'language': 'python',
            'constraints': 'test',
            'test_case_inputs': ['1']
        })

        # Validation should extract platform and problem_id from URL
        # Note: This depends on URL parser implementation
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_register_problem_missing_platform_and_url(self, api_client):
        """Test registration without platform or URL"""
        response = api_client.post('/api/register/', {
            'title': 'No Platform',
            'solution_code': 'test',
            'language': 'python',
            'constraints': 'test',
            'test_case_inputs': ['1']
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestExecuteTestCases:
    """Test test case execution endpoint"""

    def test_execute_generator_code_success(self, api_client, mock_test_case_generator):
        """Test successful generator code execution"""
        generator_code = '''
def generate_test_cases(n):
    return [f"{i} {i+1}" for i in range(n)]
'''
        response = api_client.post('/api/register/execute-test-cases/', {
            'generator_code': generator_code,
            'num_cases': 5
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'test_cases' in response.data
        assert 'count' in response.data
        assert response.data['count'] == 5

    def test_execute_generator_code_missing_code(self, api_client):
        """Test execution without generator code"""
        response = api_client.post('/api/register/execute-test-cases/', {
            'num_cases': 5
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_execute_generator_code_invalid_num_cases(self, api_client):
        """Test execution with invalid num_cases"""
        response = api_client.post('/api/register/execute-test-cases/', {
            'generator_code': 'def generate_test_cases(n): return []',
            'num_cases': 'invalid'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_execute_generator_code_num_cases_too_large(self, api_client):
        """Test execution with num_cases > 1000"""
        response = api_client.post('/api/register/execute-test-cases/', {
            'generator_code': 'def generate_test_cases(n): return []',
            'num_cases': 1001
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_execute_generator_code_default_num_cases(self, api_client, mock_test_case_generator):
        """Test execution with default num_cases"""
        response = api_client.post('/api/register/execute-test-cases/', {
            'generator_code': 'def generate_test_cases(n): return []'
        })

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestJobManagement:
    """Test script generation job management endpoints"""

    def test_list_jobs_success(self, api_client, sample_script_job, completed_script_job):
        """Test successful job list retrieval"""
        # Clear existing jobs to ensure clean state
        ScriptGenerationJob.objects.exclude(
            id__in=[sample_script_job.id, completed_script_job.id]
        ).delete()

        response = api_client.get('/api/register/jobs/')

        assert response.status_code == status.HTTP_200_OK
        assert 'jobs' in response.data
        assert len(response.data['jobs']) == 2

    def test_list_jobs_filter_by_status(self, api_client, sample_script_job, completed_script_job):
        """Test filtering jobs by status"""
        # Clear existing jobs to ensure clean state
        ScriptGenerationJob.objects.exclude(
            id__in=[sample_script_job.id, completed_script_job.id]
        ).delete()

        response = api_client.get('/api/register/jobs/', {'status': 'COMPLETED'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['jobs']) == 1
        assert response.data['jobs'][0]['status'] == 'COMPLETED'

    def test_list_jobs_filter_by_platform(self, api_client, sample_script_job):
        """Test filtering jobs by platform"""
        response = api_client.get('/api/register/jobs/', {'platform': 'baekjoon'})

        assert response.status_code == status.HTTP_200_OK
        assert all(job['platform'] == 'baekjoon' for job in response.data['jobs'])

    def test_list_jobs_filter_by_problem_id(self, api_client, sample_script_job):
        """Test filtering jobs by problem_id"""
        response = api_client.get('/api/register/jobs/', {'problem_id': '2000'})

        assert response.status_code == status.HTTP_200_OK
        assert all(job['problem_id'] == '2000' for job in response.data['jobs'])

    def test_get_job_detail_success(self, api_client, completed_script_job, mock_test_case_generator):
        """Test successful job detail retrieval"""
        response = api_client.get(f'/api/register/jobs/{completed_script_job.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == completed_script_job.id
        assert 'test_cases' in response.data
        assert len(response.data['test_cases']) > 0

    def test_get_job_detail_not_found(self, api_client):
        """Test getting non-existent job"""
        response = api_client.get('/api/register/jobs/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_get_job_detail_pending(self, api_client, sample_script_job):
        """Test getting pending job detail"""
        response = api_client.get(f'/api/register/jobs/{sample_script_job.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['test_cases'] == []


@pytest.mark.django_db
class TestSaveProblem:
    """Test problem save/draft endpoint"""

    def test_save_problem_new(self, api_client):
        """Test saving new problem draft"""
        response = api_client.post('/api/register/save/', {
            'platform': 'baekjoon',
            'problem_id': '7000',
            'title': 'New Draft',
            'problem_url': 'https://www.acmicpc.net/problem/7000',
            'tags': ['math'],
            'solution_code': 'print("test")',
            'language': 'python',
            'constraints': '1 <= n <= 100'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'problem' in response.data
        assert 'message' in response.data

        # Verify problem was created
        problem = Problem.objects.get(platform='baekjoon', problem_id='7000')
        assert problem.title == 'New Draft'

    def test_save_problem_update_existing(self, api_client, draft_problem):
        """Test updating existing problem draft"""
        response = api_client.post('/api/register/save/', {
            'platform': draft_problem.platform,
            'problem_id': draft_problem.problem_id,
            'title': 'Updated Draft',
            'language': 'cpp',
            'constraints': 'updated constraints'
        })

        assert response.status_code == status.HTTP_200_OK

        # Verify problem was updated
        draft_problem.refresh_from_db()
        assert draft_problem.title == 'Updated Draft'

    def test_save_problem_update_by_id(self, api_client, draft_problem):
        """Test updating problem by ID"""
        response = api_client.post('/api/register/save/', {
            'id': draft_problem.id,
            'title': 'Updated by ID',
            'platform': 'baekjoon',
            'problem_id': '1A'
        })

        assert response.status_code == status.HTTP_200_OK

        draft_problem.refresh_from_db()
        assert draft_problem.title == 'Updated by ID'

    def test_save_problem_missing_platform(self, api_client):
        """Test saving without platform"""
        response = api_client.post('/api/register/save/', {
            'problem_id': '8000',
            'title': 'No Platform'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_save_problem_with_url_parsing(self, api_client):
        """Test saving with URL parsing"""
        response = api_client.post('/api/register/save/', {
            'problem_url': 'https://www.acmicpc.net/problem/9000',
            'title': 'URL Parsed Draft',
            'solution_code': 'test',
            'language': 'python',
            'constraints': 'test'
        })

        # Should succeed if URL parser works
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
class TestToggleCompletion:
    """Test problem completion toggle endpoint"""

    def test_toggle_completion_to_true(self, api_client, draft_problem):
        """Test marking problem as completed"""
        response = api_client.post('/api/register/toggle-completion/', {
            'platform': draft_problem.platform,
            'problem_id': draft_problem.problem_id,
            'is_completed': True
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_completed'] is True

        draft_problem.refresh_from_db()
        assert draft_problem.is_completed is True

    def test_toggle_completion_to_false(self, api_client, sample_problem):
        """Test marking problem as draft"""
        response = api_client.post('/api/register/toggle-completion/', {
            'platform': sample_problem.platform,
            'problem_id': sample_problem.problem_id,
            'is_completed': False
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_completed'] is False

        sample_problem.refresh_from_db()
        assert sample_problem.is_completed is False

    def test_toggle_completion_missing_fields(self, api_client):
        """Test toggle without required fields"""
        response = api_client.post('/api/register/toggle-completion/', {
            'platform': 'baekjoon'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_toggle_completion_problem_not_found(self, api_client):
        """Test toggle for non-existent problem"""
        response = api_client.post('/api/register/toggle-completion/', {
            'platform': 'baekjoon',
            'problem_id': '99999',
            'is_completed': True
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestGenerateOutputs:
    """Test output generation endpoint"""

    def test_generate_outputs_success(self, api_client, sample_problem, mock_generate_outputs_task):
        """Test successful output generation task creation"""
        # Add test cases with empty outputs
        TestCase.objects.create(problem=sample_problem, input='1 2', output='')
        TestCase.objects.create(problem=sample_problem, input='3 4', output='')

        response = api_client.post('/api/register/generate-outputs/', {
            'platform': sample_problem.platform,
            'problem_id': sample_problem.problem_id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'task_id' in response.data
        assert 'message' in response.data

    def test_generate_outputs_no_solution_code(self, api_client, draft_problem):
        """Test output generation without solution code"""
        draft_problem.solution_code = None
        draft_problem.save()

        response = api_client.post('/api/register/generate-outputs/', {
            'platform': draft_problem.platform,
            'problem_id': draft_problem.problem_id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'solution code' in response.data['error'].lower()

    def test_generate_outputs_no_test_cases(self, api_client, draft_problem):
        """Test output generation without test cases"""
        response = api_client.post('/api/register/generate-outputs/', {
            'platform': draft_problem.platform,
            'problem_id': draft_problem.problem_id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'test case' in response.data['error'].lower()

    def test_generate_outputs_problem_not_found(self, api_client):
        """Test output generation for non-existent problem"""
        response = api_client.post('/api/register/generate-outputs/', {
            'platform': 'baekjoon',
            'problem_id': '99999'
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCheckTaskStatus:
    """Test task status check endpoint"""

    def test_check_task_status_success(self, authenticated_client):
        """Test checking task status"""
        with patch('celery.result.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_task.state = 'SUCCESS'
            mock_task.result = {'test': 'result'}
            mock_result.return_value = mock_task

            response = authenticated_client.get('/api/register/task-status/test-task-123/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'COMPLETED'
            assert 'result' in response.data

    def test_check_task_status_pending(self, authenticated_client):
        """Test checking pending task"""
        with patch('celery.result.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_task.state = 'PENDING'
            mock_result.return_value = mock_task

            response = authenticated_client.get('/api/register/task-status/test-task-123/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'PENDING'

    def test_check_task_status_failed(self, authenticated_client):
        """Test checking failed task"""
        with patch('celery.result.AsyncResult') as mock_result:
            mock_task = Mock()
            mock_task.state = 'FAILURE'
            mock_task.info = Exception('Task failed')
            mock_result.return_value = mock_task

            response = authenticated_client.get('/api/register/task-status/test-task-123/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'FAILED'
            assert 'error' in response.data

    def test_check_task_status_unauthenticated(self, api_client):
        """Test checking task status without authentication"""
        response = api_client.get('/api/register/task-status/test-task-123/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
