"""Tests for problem views - Async Version"""
import pytest
from rest_framework import status
from api.models import Problem, TestCase
from django.test import override_settings
from asgiref.sync import sync_to_async


@pytest.mark.django_db
@pytest.mark.asyncio
class TestProblemList:
    """Test problem list endpoint"""

    async def test_list_problems_success(self, api_client, sample_problems):
        """Test successful problem list retrieval (async)"""
        # Clear existing problems to ensure clean state - async
        await sync_to_async(Problem.objects.all().delete)()

        # Recreate sample problems - async
        from api.models import TestCase
        import uuid
        problems = []
        for i in range(3):
            problem, _ = await sync_to_async(Problem.objects.get_or_create)(
                platform='baekjoon' if i < 2 else 'codeforces',
                problem_id=f'test-{uuid.uuid4().hex[:8]}',
                defaults={
                    'title': f'Test Problem {i}',
                    'problem_url': f'https://example.com/{i}',
                    'tags': ['test'],
                    'language': 'python',
                    'is_completed': True
                }
            )
            await sync_to_async(TestCase.objects.create)(problem=problem, input='1', output='1')
            problems.append(problem)

        response = await sync_to_async(api_client.get)('/api/problems/')

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 3  # We just created 3 problems with test cases

    async def test_list_problems_exclude_drafts(self, api_client, sample_problems, draft_problem):
        """Test that problems without test cases are excluded from list (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/')

        assert response.status_code == status.HTTP_200_OK
        # Should only return problems with test cases
        assert len(response.data) == 3
        # Draft problem should not be in the list
        problem_keys = [(p['platform'], p['problem_id']) for p in response.data]
        assert (draft_problem['platform'], draft_problem['problem_id']) not in problem_keys

    async def test_list_problems_filter_by_platform(self, api_client, sample_problems):
        """Test filtering problems by platform (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/', {'platform': 'baekjoon'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2  # 2 baekjoon problems in sample_problems
        assert all(p['platform'] == 'baekjoon' for p in response.data)

    async def test_list_problems_search_by_title(self, api_client, sample_problems):
        """Test searching problems by title (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/', {'search': 'A+B'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any('A+B' in p['title'] for p in response.data)

    async def test_list_problems_search_by_problem_id(self, api_client, sample_problems):
        """Test searching problems by problem_id (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/', {'search': '1000'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any('1000' in p['problem_id'] for p in response.data)

    async def test_list_problems_search_case_insensitive(self, api_client, sample_problems):
        """Test case-insensitive search (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/', {'search': 'theatre'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    async def test_list_problems_empty_result(self, api_client):
        """Test list when no problems exist (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    async def test_list_problems_combined_filters(self, api_client, sample_problems):
        """Test combining platform filter and search (async)"""
        response = await sync_to_async(api_client.get)('/api/problems/', {
            'platform': 'baekjoon',
            'search': 'A+B'
        })

        assert response.status_code == status.HTTP_200_OK
        assert all(p['platform'] == 'baekjoon' for p in response.data)
        assert all('A+B' in p['title'] or 'A+B' in p['problem_id'] for p in response.data)

    def test_list_problems_ordering(self, api_client, sample_problems):
        """Test that problems are ordered by most recent"""
        response = api_client.get('/api/problems/')

        assert response.status_code == status.HTTP_200_OK
        # Check that results are in descending order by creation time
        if len(response.data) > 1:
            for i in range(len(response.data) - 1):
                assert response.data[i]['created_at'] >= response.data[i + 1]['created_at']


@pytest.mark.django_db
class TestProblemDetail:
    """Test problem detail endpoint"""

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_by_id_success(self, authenticated_client, sample_user, sample_problem, sample_test_cases):
        """Test successful problem retrieval by ID (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get(f'/api/problems/{sample_problem["platform"]}/{sample_problem["problem_id"]}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['platform'] == sample_problem['platform']
        assert response.data['problem_id'] == sample_problem['problem_id']
        assert response.data['title'] == sample_problem['title']
        assert 'test_cases' in response.data
        assert len(response.data['test_cases']) == 3

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_by_platform_and_id_success(self, authenticated_client, sample_user, sample_problem, sample_test_cases):
        """Test successful problem retrieval by platform and problem_id (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get(
            f'/api/problems/{sample_problem["platform"]}/{sample_problem["problem_id"]}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['platform'] == sample_problem['platform']
        assert response.data['problem_id'] == sample_problem['problem_id']
        assert 'test_cases' in response.data

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_not_found_by_id(self, authenticated_client, sample_user):
        """Test getting non-existent problem by ID (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get('/api/problems/baekjoon/99999/')

        # Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_not_found_by_platform_id(self, authenticated_client, sample_user):
        """Test getting non-existent problem by platform and problem_id (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get('/api/problems/baekjoon/99999/')

        # Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_includes_test_cases(self, authenticated_client, sample_user, sample_problem, sample_test_cases):
        """Test that problem detail includes test cases (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get(f'/api/problems/{sample_problem["platform"]}/{sample_problem["problem_id"]}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'test_cases' in response.data
        test_cases = response.data['test_cases']
        assert len(test_cases) == len(sample_test_cases)

        # Verify test case structure
        for tc in test_cases:
            assert 'id' in tc
            assert 'input' in tc
            assert 'output' in tc

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_with_no_test_cases(self, authenticated_client, sample_user, draft_problem):
        """Test getting a problem with no test cases (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get(f'/api/problems/{draft_problem["platform"]}/{draft_problem["problem_id"]}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['test_cases'] == []

    @override_settings(ADMIN_EMAILS=['test@example.com'])
    def test_get_problem_includes_metadata(self, authenticated_client, sample_user, sample_problem):
        """Test that problem detail includes all metadata (admin only)"""
        client = authenticated_client(sample_user)
        response = client.get(f'/api/problems/{sample_problem["platform"]}/{sample_problem["problem_id"]}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'tags' in response.data
        assert 'solution_code' in response.data
        assert 'language' in response.data
        assert 'constraints' in response.data
        assert 'is_completed' in response.data


@pytest.mark.django_db
class TestProblemDrafts:
    """Test problem drafts endpoint"""

    def test_get_drafts_success(self, api_client, draft_problem):
        """Test successful retrieval of draft problems"""
        response = api_client.get('/api/problems/drafts/')

        assert response.status_code == status.HTTP_200_OK
        assert 'drafts' in response.data
        # Check that our draft_problem is in the response
        draft_ids = [d['id'] for d in response.data['drafts']]
        assert draft_problem.id in draft_ids

    def test_get_drafts_exclude_completed(self, api_client, sample_problems, draft_problem):
        """Test that completed problems are excluded from drafts"""
        response = api_client.get('/api/problems/drafts/')

        assert response.status_code == status.HTTP_200_OK
        draft_ids = [d['id'] for d in response.data['drafts']]
        # Only draft_problem should be in drafts
        assert draft_problem.id in draft_ids
        # Problems with test cases should not be in drafts
        for problem in sample_problems:
            assert problem.id not in draft_ids

    def test_get_drafts_empty(self, api_client, sample_problems):
        """Test drafts endpoint when no drafts exist"""
        # Clear all existing drafts to ensure clean state
        from django.db.models import Count
        Problem.objects.annotate(
            test_case_count=Count('test_cases')
        ).filter(test_case_count=0).delete()

        response = api_client.get('/api/problems/drafts/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['drafts'] == []

    def test_get_drafts_ordering(self, api_client):
        """Test that drafts are ordered by most recent"""
        # Create multiple drafts
        draft1 = Problem.objects.create(
            platform='baekjoon',
            problem_id='5000',
            title='Draft 1',
            language='python'
        )
        draft2 = Problem.objects.create(
            platform='baekjoon',
            problem_id='5001',
            title='Draft 2',
            language='python'
        )

        response = api_client.get('/api/problems/drafts/')

        assert response.status_code == status.HTTP_200_OK
        drafts = response.data['drafts']

        # Find our two drafts in the response
        our_drafts = [d for d in drafts if d['id'] in [draft1.id, draft2.id]]
        assert len(our_drafts) == 2

        # Check that our drafts are in descending order
        draft_positions = {d['id']: i for i, d in enumerate(drafts)}
        # draft2 was created later, so should appear before draft1
        assert draft_positions[draft2.id] < draft_positions[draft1.id]


@pytest.mark.django_db
class TestProblemRegistered:
    """Test registered problems endpoint"""

    def test_get_registered_problems_success(self, api_client, sample_problems):
        """Test successful retrieval of registered problems"""
        response = api_client.get('/api/problems/registered/')

        assert response.status_code == status.HTTP_200_OK
        assert 'problems' in response.data
        assert len(response.data['problems']) == 3

    def test_get_registered_exclude_drafts(self, api_client, sample_problems, draft_problem):
        """Test that drafts are excluded from registered problems"""
        response = api_client.get('/api/problems/registered/')

        assert response.status_code == status.HTTP_200_OK
        problem_ids = [p['id'] for p in response.data['problems']]
        assert draft_problem.id not in problem_ids
        for problem in sample_problems:
            assert problem.id in problem_ids

    def test_get_registered_empty(self, api_client, draft_problem):
        """Test registered endpoint when only drafts exist"""
        response = api_client.get('/api/problems/registered/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['problems'] == []

    def test_get_registered_includes_test_case_count(self, api_client, sample_problems):
        """Test that registered problems include test case count"""
        response = api_client.get('/api/problems/registered/')

        assert response.status_code == status.HTTP_200_OK
        for problem in response.data['problems']:
            assert 'test_case_count' in problem
            assert problem['test_case_count'] > 0


@pytest.mark.django_db
class TestProblemQueryOptimization:
    """Test query optimization for problem endpoints"""

    def test_list_problems_query_count(self, api_client, sample_problems, django_assert_num_queries):
        """Test that problem list uses optimized queries"""
        # Should use minimal queries (1 for problems + 1 for count)
        with django_assert_num_queries(1):
            response = api_client.get('/api/problems/')
            assert response.status_code == status.HTTP_200_OK

    def test_problem_detail_query_count(self, api_client, sample_problem, sample_test_cases, django_assert_num_queries):
        """Test that problem detail uses prefetch_related for test cases"""
        # Should use 2 queries (1 for problem, 1 for test cases with prefetch_related)
        with django_assert_num_queries(2):
            response = api_client.get(f'/api/problems/{sample_problem.id}/')
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProblemDelete:
    """Test problem deletion endpoint"""

    def test_delete_problem_by_id_success(self, api_client, sample_problem, sample_test_cases):
        """Test successful problem deletion by ID"""
        problem_id = sample_problem.id
        test_case_ids = [tc.id for tc in sample_test_cases]

        response = api_client.delete(f'/api/problems/{problem_id}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'deleted successfully' in response.data['message'].lower()

        # Verify problem was deleted
        assert not Problem.objects.filter(id=problem_id).exists()

        # Verify test cases were deleted (CASCADE)
        for tc_id in test_case_ids:
            assert not TestCase.objects.filter(id=tc_id).exists()

    def test_delete_problem_by_platform_and_id_success(self, api_client, sample_problem, sample_test_cases):
        """Test successful problem deletion by platform and problem_id"""
        platform = sample_problem.platform
        problem_id_str = sample_problem.problem_id
        problem_pk = sample_problem.id

        response = api_client.delete(f'/api/problems/{platform}/{problem_id_str}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

        # Verify problem was deleted
        assert not Problem.objects.filter(id=problem_pk).exists()

    def test_delete_problem_not_found_by_id(self, api_client):
        """Test deleting non-existent problem by ID"""
        response = api_client.delete('/api/problems/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        assert 'not found' in response.data['error'].lower()

    def test_delete_problem_not_found_by_platform_id(self, api_client):
        """Test deleting non-existent problem by platform and problem_id"""
        response = api_client.delete('/api/problems/baekjoon/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_delete_problem_cascades_to_test_cases(self, api_client, sample_problem):
        """Test that deleting a problem also deletes its test cases"""
        # Create test cases
        tc1 = TestCase.objects.create(problem=sample_problem, input='1', output='1')
        tc2 = TestCase.objects.create(problem=sample_problem, input='2', output='2')
        tc3 = TestCase.objects.create(problem=sample_problem, input='3', output='3')

        problem_id = sample_problem.id
        test_case_ids = [tc1.id, tc2.id, tc3.id]

        # Delete problem
        response = api_client.delete(f'/api/problems/{problem_id}/')

        assert response.status_code == status.HTTP_200_OK

        # Verify all test cases were deleted
        for tc_id in test_case_ids:
            assert not TestCase.objects.filter(id=tc_id).exists()

    def test_delete_draft_problem(self, api_client, draft_problem):
        """Test deleting a draft problem (no test cases)"""
        problem_id = draft_problem.id

        response = api_client.delete(f'/api/problems/{problem_id}/')

        assert response.status_code == status.HTTP_200_OK
        assert not Problem.objects.filter(id=problem_id).exists()

    def test_delete_problem_with_solution_code(self, api_client):
        """Test deleting a problem with solution code"""
        problem = Problem.objects.create(
            platform='baekjoon',
            problem_id='6666',
            title='Problem with Solution',
            solution_code='print("test")',
            language='python'
        )
        problem_id = problem.id

        response = api_client.delete(f'/api/problems/{problem_id}/')

        assert response.status_code == status.HTTP_200_OK
        assert not Problem.objects.filter(id=problem_id).exists()


@pytest.mark.django_db
class TestProblemEdgeCases:
    """Test edge cases for problem endpoints"""

    def test_problem_with_special_characters_in_title(self, api_client):
        """Test problem with special characters in title"""
        problem = Problem.objects.create(
            platform='baekjoon',
            problem_id='9999',
            title='Test & <Special> "Characters"',
            language='python',
            is_completed=True
        )
        TestCase.objects.create(problem=problem, input='1', output='1')

        response = api_client.get('/api/problems/')

        assert response.status_code == status.HTTP_200_OK
        assert any(p['title'] == 'Test & <Special> "Characters"' for p in response.data)

    def test_problem_with_empty_tags(self, api_client):
        """Test problem with empty tags"""
        problem = Problem.objects.create(
            platform='baekjoon',
            problem_id='8888',
            title='No Tags Problem',
            tags=[],
            language='python',
            is_completed=True
        )
        TestCase.objects.create(problem=problem, input='1', output='1')

        response = api_client.get(f'/api/problems/{problem.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['tags'] == []

    def test_problem_with_long_constraints(self, api_client):
        """Test problem with very long constraints"""
        long_constraints = 'A' * 10000
        problem = Problem.objects.create(
            platform='baekjoon',
            problem_id='7777',
            title='Long Constraints',
            constraints=long_constraints,
            language='python',
            is_completed=True
        )

        response = api_client.get(f'/api/problems/{problem.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['constraints']) == 10000
