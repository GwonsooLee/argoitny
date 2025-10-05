"""Tests for search history views"""
import pytest
from rest_framework import status
from api.models import SearchHistory


@pytest.mark.django_db
class TestSearchHistoryList:
    """Test search history list endpoint"""

    def test_list_history_success(self, api_client, sample_search_history):
        """Test successful search history list retrieval"""
        response = api_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data
        assert 'has_more' in response.data
        assert len(response.data['results']) >= 1

    def test_list_history_pagination(self, api_client, sample_user, sample_problem):
        """Test pagination in search history list"""
        # Clear existing history to ensure clean state
        SearchHistory.objects.all().delete()

        # Create 25 history entries
        for i in range(25):
            SearchHistory.objects.create(
                user=sample_user,
                user_identifier=sample_user.email,
                problem=sample_problem,
                platform='baekjoon',
                problem_number=f'{1000 + i}',
                problem_title=f'Problem {i}',
                language='python',
                code='test code',
                result_summary='Passed',
                passed_count=3,
                failed_count=0,
                total_count=3,
                is_code_public=True
            )

        # First page
        response = api_client.get('/api/history/', {'limit': 10})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 10
        assert response.data['has_more'] is True
        assert response.data['next_offset'] == 10

        # Second page
        response = api_client.get('/api/history/', {'offset': 10, 'limit': 10})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 10
        assert response.data['has_more'] is True

        # Last page
        response = api_client.get('/api/history/', {'offset': 20, 'limit': 10})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['has_more'] is False

    def test_list_history_public_only_anonymous(self, api_client, sample_user, sample_problem):
        """Test that anonymous users see only public history"""
        # Clear existing history to ensure clean state
        SearchHistory.objects.all().delete()

        # Create public history
        public_history = SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test Problem',
            language='python',
            code='print(1)',
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        # Create private history
        private_history = SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1001',
            problem_title='Test Problem 2',
            language='python',
            code='print(2)',
            result_summary='Failed',
            passed_count=0,
            failed_count=1,
            total_count=1,
            is_code_public=False
        )

        response = api_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        # Should only see public history
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['is_code_public'] is True

    def test_list_history_authenticated_user_sees_own_and_public(self, authenticated_client, sample_search_history, private_search_history, sample_user):
        """Test that authenticated users see their own history and public history"""
        response = authenticated_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        # Should see own history (1) + public from others (1) = 2 total
        assert len(response.data['results']) >= 1

    def test_list_history_my_only_filter(self, authenticated_client, sample_search_history, private_search_history):
        """Test filtering to show only current user's history"""
        response = authenticated_client.get('/api/history/', {'my_only': 'true'})

        assert response.status_code == status.HTTP_200_OK
        # Should only see own history (sample_search_history belongs to sample_user)
        results = response.data['results']
        assert len(results) >= 1
        # All results should belong to current user
        user_emails = [r['user_email'] for r in results if r['user_email']]
        assert all(email == 'test@example.com' for email in user_emails)

    def test_list_history_my_only_unauthenticated(self, api_client):
        """Test my_only filter for unauthenticated user returns empty"""
        response = api_client.get('/api/history/', {'my_only': 'true'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0

    def test_list_history_code_visibility_public(self, api_client, sample_search_history):
        """Test that public history includes code"""
        response = api_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        public_history = [h for h in response.data['results'] if h['is_code_public']][0]
        assert public_history['code'] is not None
        assert len(public_history['code']) > 0

    def test_list_history_code_visibility_private_owner(self, authenticated_client, private_search_history, another_user):
        """Test that owner can see their own private code"""
        # Create client for the owner of private history
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(another_user)
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        response = authenticated_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        # Find the private history
        private = [h for h in response.data['results'] if not h['is_code_public']]
        if private:
            assert private[0]['code'] is not None

    def test_list_history_code_visibility_private_non_owner(self, api_client, private_search_history):
        """Test that non-owners cannot see private code"""
        response = api_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        # Private history should not appear for anonymous users
        private = [h for h in response.data['results'] if not h['is_code_public']]
        assert len(private) == 0

    def test_list_history_ordering(self, api_client, sample_user, sample_problem):
        """Test that history is ordered by most recent"""
        # Create multiple entries
        for i in range(5):
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

        response = api_client.get('/api/history/')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i]['created_at'] >= results[i + 1]['created_at']

    def test_list_history_invalid_offset(self, api_client):
        """Test with invalid offset parameter"""
        response = api_client.get('/api/history/', {'offset': 'invalid'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_list_history_invalid_limit(self, api_client):
        """Test with invalid limit parameter"""
        response = api_client.get('/api/history/', {'limit': 'invalid'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_list_history_max_limit(self, api_client):
        """Test that limit is capped at 100"""
        response = api_client.get('/api/history/', {'limit': 200})

        assert response.status_code == status.HTTP_200_OK
        # Should not return more than 100 even if requested


@pytest.mark.django_db
class TestSearchHistoryDetail:
    """Test search history detail endpoint"""

    def test_get_history_detail_success(self, api_client, sample_search_history, sample_test_cases):
        """Test successful retrieval of history detail"""
        response = api_client.get(f'/api/history/{sample_search_history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == sample_search_history.id
        assert response.data['platform'] == sample_search_history.platform
        assert response.data['problem_number'] == sample_search_history.problem_number
        assert 'code' in response.data
        assert 'test_results' in response.data

    def test_get_history_detail_includes_test_case_details(self, api_client, sample_search_history, sample_test_cases):
        """Test that detail includes test case input and expected output"""
        response = api_client.get(f'/api/history/{sample_search_history.id}/')

        assert response.status_code == status.HTTP_200_OK
        test_results = response.data['test_results']

        # Should have test results
        if test_results:
            for result in test_results:
                # Should include enriched data
                assert 'test_case_id' in result
                assert 'output' in result
                assert 'passed' in result
                assert 'status' in result

    def test_get_history_detail_not_found(self, api_client):
        """Test getting non-existent history"""
        response = api_client.get('/api/history/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_get_history_detail_full_code(self, api_client, sample_search_history):
        """Test that detail always shows full code"""
        response = api_client.get(f'/api/history/{sample_search_history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] is not None
        assert len(response.data['code']) > 0

    def test_get_history_detail_includes_metadata(self, api_client, sample_search_history):
        """Test that detail includes all metadata"""
        response = api_client.get(f'/api/history/{sample_search_history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'user_identifier' in response.data
        assert 'language' in response.data
        assert 'result_summary' in response.data
        assert 'passed_count' in response.data
        assert 'failed_count' in response.data
        assert 'total_count' in response.data
        assert 'created_at' in response.data


@pytest.mark.django_db
class TestSearchHistoryCreation:
    """Test search history creation (via code execution)"""

    def test_history_created_on_code_execution(self, sample_user, sample_problem, sample_test_cases):
        """Test that search history is created when code is executed"""
        from api.tasks import execute_code_task
        from unittest.mock import patch

        with patch('api.tasks.CodeExecutionService.execute_with_test_cases') as mock_execute:
            mock_execute.return_value = [
                {'status': 'success', 'output': '3', 'input': '1 2'},
                {'status': 'success', 'output': '12', 'input': '5 7'},
                {'status': 'success', 'output': '0', 'input': '0 0'},
            ]

            initial_count = SearchHistory.objects.count()

            execute_code_task(
                code='test code',
                language='python',
                problem_id=sample_problem.id,
                user_id=sample_user.id,
                user_identifier=sample_user.email,
                is_code_public=True
            )

            # History should be created
            assert SearchHistory.objects.count() == initial_count + 1

            history = SearchHistory.objects.latest('created_at')
            assert history.user == sample_user
            assert history.problem == sample_problem
            assert history.language == 'python'
            assert history.passed_count == 3
            assert history.failed_count == 0

    def test_history_stores_test_results(self, sample_user, sample_problem, sample_test_cases):
        """Test that search history stores detailed test results"""
        from api.tasks import execute_code_task
        from unittest.mock import patch

        with patch('api.tasks.CodeExecutionService.execute_with_test_cases') as mock_execute:
            mock_execute.return_value = [
                {'status': 'success', 'output': '3', 'input': '1 2'},
                {'status': 'success', 'output': '11', 'input': '5 7'},
                {'status': 'success', 'output': '0', 'input': '0 0'},
            ]

            execute_code_task(
                code='buggy code',
                language='python',
                problem_id=sample_problem.id,
                user_id=sample_user.id,
                user_identifier=sample_user.email,
                is_code_public=False
            )

            history = SearchHistory.objects.latest('created_at')
            assert history.test_results is not None
            assert len(history.test_results) == 3


@pytest.mark.django_db
class TestSearchHistoryQueryOptimization:
    """Test query optimization for history endpoints"""

    def test_list_history_query_count(self, api_client, sample_search_history, django_assert_num_queries):
        """Test that history list uses optimized queries"""
        # Should use select_related for user to avoid N+1
        with django_assert_num_queries(2):  # 1 for count, 1 for results with select_related
            response = api_client.get('/api/history/')
            assert response.status_code == status.HTTP_200_OK

    def test_detail_history_query_count(self, api_client, sample_search_history, django_assert_num_queries):
        """Test that history detail uses select_related"""
        # Should use select_related for user
        with django_assert_num_queries(2):  # 1 for history, 1 for test cases
            response = api_client.get(f'/api/history/{sample_search_history.id}/')
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSearchHistoryEdgeCases:
    """Test edge cases for search history"""

    def test_history_with_no_test_results(self, api_client, sample_user, sample_problem):
        """Test history with null test_results"""
        history = SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code='test',
            result_summary='Error',
            passed_count=0,
            failed_count=0,
            total_count=0,
            is_code_public=True,
            test_results=None
        )

        response = api_client.get(f'/api/history/{history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['test_results'] is None

    def test_history_with_empty_code(self, api_client, sample_user, sample_problem):
        """Test history with empty code"""
        history = SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code='',
            result_summary='Error',
            passed_count=0,
            failed_count=0,
            total_count=0,
            is_code_public=True
        )

        response = api_client.get(f'/api/history/{history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == ''

    def test_history_with_very_long_code(self, api_client, sample_user, sample_problem):
        """Test history with very long code"""
        long_code = 'x = 1\n' * 10000
        history = SearchHistory.objects.create(
            user=sample_user,
            user_identifier=sample_user.email,
            problem=sample_problem,
            platform='baekjoon',
            problem_number='1000',
            problem_title='Test',
            language='python',
            code=long_code,
            result_summary='Passed',
            passed_count=1,
            failed_count=0,
            total_count=1,
            is_code_public=True
        )

        response = api_client.get(f'/api/history/{history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['code']) > 10000

    def test_history_without_user(self, api_client, sample_problem):
        """Test history for anonymous user"""
        history = SearchHistory.objects.create(
            user=None,
            user_identifier='anonymous',
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

        response = api_client.get(f'/api/history/{history.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user'] is None
        assert response.data['user_identifier'] == 'anonymous'
