"""Tests for code execution views"""
import pytest
from rest_framework import status
from unittest.mock import patch, Mock
from api.models import SearchHistory


@pytest.mark.django_db
class TestExecuteCode:
    """Test code execution endpoint"""

    def test_execute_code_success(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test successful code execution task creation"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'problem_id': sample_problem.id,
            'user_identifier': 'test@example.com',
            'is_code_public': True
        })

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'task_id' in response.data
        assert 'message' in response.data
        assert 'started' in response.data['message'].lower()

    def test_execute_code_missing_code(self, authenticated_client, sample_problem):
        """Test execution without code"""
        response = authenticated_client.post('/api/execute/', {
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_execute_code_missing_language(self, authenticated_client, sample_problem):
        """Test execution without language"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_execute_code_missing_problem_id(self, authenticated_client):
        """Test execution without problem_id"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_execute_code_invalid_problem_id(self, authenticated_client):
        """Test execution with non-existent problem"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python',
            'problem_id': 99999
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_execute_code_problem_without_test_cases(self, authenticated_client, draft_problem):
        """Test execution on problem with no test cases"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python',
            'problem_id': draft_problem.id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'test case' in response.data['error'].lower()

    def test_execute_code_unauthenticated(self, api_client, sample_problem):
        """Test execution without authentication"""
        response = api_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_execute_code_default_user_identifier(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test execution with default user_identifier"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_execute_code_default_is_code_public(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test execution with default is_code_public (False)"""
        response = authenticated_client.post('/api/execute/', {
            'code': 'print("test")',
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_execute_code_with_different_languages(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test execution with different programming languages"""
        languages = ['python', 'cpp', 'java', 'javascript']

        for lang in languages:
            response = authenticated_client.post('/api/execute/', {
                'code': 'test code',
                'language': lang,
                'problem_id': sample_problem.id
            })

            assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.django_db
class TestExecuteCodeTask:
    """Test code execution Celery task"""

    @patch('api.tasks.CodeExecutionService.execute_with_test_cases')
    def test_execute_code_task_success(self, mock_execute, sample_user, sample_problem, sample_test_cases):
        """Test successful code execution task"""
        from api.tasks import execute_code_task

        # Mock successful execution
        mock_execute.return_value = [
            {'status': 'success', 'output': '3', 'input': '1 2'},
            {'status': 'success', 'output': '12', 'input': '5 7'},
            {'status': 'success', 'output': '0', 'input': '0 0'},
        ]

        result = execute_code_task(
            code='a, b = map(int, input().split())\nprint(a + b)',
            language='python',
            problem_id=sample_problem.id,
            user_id=sample_user.id,
            user_identifier=sample_user.email,
            is_code_public=True
        )

        assert result['status'] == 'COMPLETED'
        assert 'results' in result
        assert 'summary' in result
        assert result['summary']['passed'] == 3
        assert result['summary']['failed'] == 0

        # Verify search history was created
        history = SearchHistory.objects.filter(user=sample_user).first()
        assert history is not None
        assert history.passed_count == 3
        assert history.failed_count == 0
        assert history.is_code_public is True

    @patch('api.tasks.CodeExecutionService.execute_with_test_cases')
    def test_execute_code_task_partial_failure(self, mock_execute, sample_user, sample_problem, sample_test_cases):
        """Test code execution task with some failing tests"""
        from api.tasks import execute_code_task

        # Mock partial failure
        mock_execute.return_value = [
            {'status': 'success', 'output': '3', 'input': '1 2'},
            {'status': 'success', 'output': '11', 'input': '5 7'},  # Wrong output
            {'status': 'success', 'output': '0', 'input': '0 0'},
        ]

        result = execute_code_task(
            code='buggy code',
            language='python',
            problem_id=sample_problem.id,
            user_id=sample_user.id,
            user_identifier=sample_user.email,
            is_code_public=False
        )

        assert result['status'] == 'COMPLETED'
        assert result['summary']['passed'] == 2
        assert result['summary']['failed'] == 1

        # Verify search history
        history = SearchHistory.objects.filter(user=sample_user).first()
        assert history is not None
        assert history.passed_count == 2
        assert history.failed_count == 1
        assert history.result_summary == 'Failed'

    @patch('api.tasks.CodeExecutionService.execute_with_test_cases')
    def test_execute_code_task_execution_error(self, mock_execute, sample_user, sample_problem, sample_test_cases):
        """Test code execution task with execution errors"""
        from api.tasks import execute_code_task

        # Mock execution error
        mock_execute.return_value = [
            {'status': 'error', 'output': '', 'input': '1 2', 'error': 'SyntaxError'},
            {'status': 'error', 'output': '', 'input': '5 7', 'error': 'SyntaxError'},
            {'status': 'error', 'output': '', 'input': '0 0', 'error': 'SyntaxError'},
        ]

        result = execute_code_task(
            code='invalid syntax',
            language='python',
            problem_id=sample_problem.id,
            user_id=sample_user.id,
            user_identifier=sample_user.email,
            is_code_public=False
        )

        assert result['status'] == 'COMPLETED'
        assert result['summary']['passed'] == 0
        assert result['summary']['failed'] == 3

    def test_execute_code_task_anonymous_user(self, sample_problem, sample_test_cases):
        """Test code execution task for anonymous user"""
        from api.tasks import execute_code_task

        with patch('api.tasks.CodeExecutionService.execute_with_test_cases') as mock_execute:
            mock_execute.return_value = [
                {'status': 'success', 'output': '3', 'input': '1 2'},
                {'status': 'success', 'output': '12', 'input': '5 7'},
                {'status': 'success', 'output': '0', 'input': '0 0'},
            ]

            result = execute_code_task(
                code='print("test")',
                language='python',
                problem_id=sample_problem.id,
                user_id=None,
                user_identifier='anonymous',
                is_code_public=True
            )

            assert result['status'] == 'COMPLETED'

            # Verify history created without user
            history = SearchHistory.objects.filter(user_identifier='anonymous').first()
            assert history is not None
            assert history.user is None

    def test_execute_code_task_problem_not_found(self):
        """Test code execution task with non-existent problem"""
        from api.tasks import execute_code_task

        result = execute_code_task(
            code='print("test")',
            language='python',
            problem_id=99999,
            user_id=None,
            user_identifier='test@example.com',
            is_code_public=False
        )

        assert result['status'] == 'FAILED'
        assert 'error' in result

    @patch('api.tasks.CodeExecutionService.execute_with_test_cases')
    def test_execute_code_task_updates_problem_metadata(self, mock_execute, sample_problem, sample_test_cases):
        """Test that execution task updates problem execution count"""
        from api.tasks import execute_code_task

        mock_execute.return_value = [
            {'status': 'success', 'output': '3', 'input': '1 2'},
        ]

        # Execute multiple times
        for i in range(3):
            execute_code_task(
                code='print("test")',
                language='python',
                problem_id=sample_problem.id,
                user_id=None,
                user_identifier='test@example.com',
                is_code_public=False
            )

        # Refresh from database
        sample_problem.refresh_from_db()
        assert sample_problem.metadata.get('execution_count') == 3


@pytest.mark.django_db
class TestExecuteCodeEdgeCases:
    """Test edge cases for code execution"""

    def test_execute_very_long_code(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test execution with very long code"""
        long_code = 'x = 1\n' * 10000

        response = authenticated_client.post('/api/execute/', {
            'code': long_code,
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_execute_code_with_special_characters(self, authenticated_client, sample_problem, sample_test_cases, mock_celery_delay):
        """Test execution with special characters in code"""
        special_code = 'print("Hello 世界 🌍")'

        response = authenticated_client.post('/api/execute/', {
            'code': special_code,
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_execute_empty_code(self, authenticated_client, sample_problem):
        """Test execution with empty code"""
        response = authenticated_client.post('/api/execute/', {
            'code': '',
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_execute_code_with_problem_having_many_test_cases(self, authenticated_client, sample_problem, mock_celery_delay):
        """Test execution with problem having many test cases"""
        from api.models import TestCase

        # Create 100 test cases
        for i in range(100):
            TestCase.objects.create(
                problem=sample_problem,
                input=f'{i} {i+1}',
                output=str(2*i + 1)
            )

        response = authenticated_client.post('/api/execute/', {
            'code': 'a, b = map(int, input().split())\nprint(a + b)',
            'language': 'python',
            'problem_id': sample_problem.id
        })

        assert response.status_code == status.HTTP_202_ACCEPTED
