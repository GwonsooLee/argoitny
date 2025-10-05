"""Tests for account views"""
import pytest
from rest_framework import status
from api.models import SearchHistory


@pytest.mark.django_db
class TestAccountStats:
    """Test account statistics endpoint"""

    def test_get_account_stats_success(self, authenticated_client, sample_user, sample_problem):
        """Test successful retrieval of account statistics"""
        # Create some search history for the user
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='A+B',
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=3,
            failed_count=0,
            total_count=3,
            is_code_public=True
        )
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1001',
            problem_title='A-B',
            language='cpp',
            code='test',
            result_summary='Failed',
            passed_count=2,
            failed_count=1,
            total_count=3,
            is_code_public=False
        )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_executions' in response.data
        assert 'by_platform' in response.data
        assert 'by_language' in response.data
        assert 'total_problems' in response.data
        assert 'passed_executions' in response.data
        assert 'failed_executions' in response.data

        assert response.data['total_executions'] == 2
        assert response.data['passed_executions'] == 1
        assert response.data['failed_executions'] == 1

    def test_get_account_stats_unauthenticated(self, api_client):
        """Test account stats without authentication"""
        response = api_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_account_stats_by_platform(self, authenticated_client, sample_user, sample_problem):
        """Test that stats correctly group by platform"""
        # Create history for different platforms
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='codeforces',
            problem_number='1A',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'baekjoon' in response.data['by_platform']
        assert 'codeforces' in response.data['by_platform']
        assert response.data['by_platform']['baekjoon'] == 1
        assert response.data['by_platform']['codeforces'] == 1

    def test_get_account_stats_by_language(self, authenticated_client, sample_user, sample_problem):
        """Test that stats correctly group by language"""
        # Create history for different languages
        languages = ['python', 'cpp', 'java', 'python', 'python']
        for lang in languages:
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number='1000',
                problem_title='Test',
                language=lang,
                code='test',
                result_summary='Passed',
                passed_count=1,
                failed_count=0,
                total_count=1,
                is_code_public=True
            )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['by_language']['python'] == 3
        assert response.data['by_language']['cpp'] == 1
        assert response.data['by_language']['java'] == 1

    def test_get_account_stats_total_problems(self, authenticated_client, sample_user, sample_problems):
        """Test that stats correctly count unique problems"""
        # Create history for same problem multiple times
        for i in range(5):
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problems[0],  # Same problem
                platform=sample_problems[0].platform,
                problem_number=sample_problems[0].problem_id,
                problem_title=sample_problems[0].title,
                language='python',
                code='test',
                result_summary='Passed',
                passed_count=1,
                failed_count=0,
                total_count=1,
                is_code_public=True
            )

        # Create history for different problem
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problems[1],  # Different problem
            platform=sample_problems[1].platform,
            problem_number=sample_problems[1].problem_id,
            problem_title=sample_problems[1].title,
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        # Should count only 2 unique problems
        assert response.data['total_problems'] == 2
        # But 6 total executions
        assert response.data['total_executions'] == 6

    def test_get_account_stats_passed_vs_failed(self, authenticated_client, sample_user, sample_problem):
        """Test that stats correctly count passed vs failed executions"""
        # Create passed executions
        for i in range(3):
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number='1000',
                problem_title='Test',
                language='python',
                code='test',
                result_summary='Passed',
                passed_count=3,
                failed_count=0,
                total_count=3,
                is_code_public=True
            )

        # Create failed executions
        for i in range(2):
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number='1000',
                problem_title='Test',
                language='python',
                code='test',
                result_summary='Failed',
                passed_count=1,
                failed_count=2,
                total_count=3,
                is_code_public=True
            )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['passed_executions'] == 3
        assert response.data['failed_executions'] == 2

    def test_get_account_stats_empty_history(self, authenticated_client):
        """Test account stats with no execution history"""
        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_executions'] == 0
        assert response.data['by_platform'] == {}
        assert response.data['by_language'] == {}
        assert response.data['total_problems'] == 0
        assert response.data['passed_executions'] == 0
        assert response.data['failed_executions'] == 0

    def test_get_account_stats_only_own_history(self, authenticated_client, sample_user, another_user, sample_problem):
        """Test that stats only include user's own history"""
        # Create history for authenticated user
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        # Create history for another user
        SearchHistory.objects.create(
            user=another_user,
            user_identifier=another_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        # Should only count own history
        assert response.data['total_executions'] == 1


@pytest.mark.django_db
class TestAccountStatsEdgeCases:
    """Test edge cases for account statistics"""

    def test_account_stats_with_multiple_platforms(self, authenticated_client, sample_user, sample_problem):
        """Test stats with many different platforms"""
        platforms = ['baekjoon', 'codeforces', 'leetcode', 'atcoder', 'hackerrank']

        for platform in platforms:
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform=platform,
                problem_number='1',
                problem_title='Test',
                language='python',
                code='test',
                result_summary='Passed',
                passed_count=1,
                failed_count=0,
                total_count=1,
                is_code_public=True
            )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['by_platform']) == 5
        for platform in platforms:
            assert platform in response.data['by_platform']
            assert response.data['by_platform'][platform] == 1

    def test_account_stats_with_multiple_languages(self, authenticated_client, sample_user, sample_problem):
        """Test stats with many different languages"""
        languages = ['python', 'cpp', 'java', 'javascript', 'go', 'rust']

        for language in languages:
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number='1',
                problem_title='Test',
                language=language,
                code='test',
                result_summary='Passed',
                passed_count=1,
                failed_count=0,
                total_count=1,
                is_code_public=True
            )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['by_language']) == 6
        for language in languages:
            assert language in response.data['by_language']

    def test_account_stats_with_partial_failures(self, authenticated_client, sample_user, sample_problem):
        """Test stats with partially failed executions"""
        # Execution with some failed test cases (failed_count > 0)
        SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Partial',
            passed_count=5,
            failed_count=3,  # Some failures
            total_count=8,
            is_code_public=True
        )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        # Should count as failed (failed_count > 0)
        assert response.data['failed_executions'] == 1
        assert response.data['passed_executions'] == 0

    def test_account_stats_performance_with_many_records(self, authenticated_client, sample_user, sample_problem):
        """Test stats performance with many execution records"""
        # Create 100 execution records
        for i in range(100):
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number=str(1000 + i),
                problem_title=f'Problem {i}',
                language='python' if i % 2 == 0 else 'cpp',
                code='test',
                result_summary='Passed' if i % 3 == 0 else 'Failed',
                passed_count=1 if i % 3 == 0 else 0,
                failed_count=0 if i % 3 == 0 else 1,
                total_count=1,
                is_code_public=True
            )

        response = authenticated_client.get('/api/account/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_executions'] == 100
        assert 'by_platform' in response.data
        assert 'by_language' in response.data
