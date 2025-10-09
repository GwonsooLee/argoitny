"""Admin-only views - DynamoDB implementation"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, datetime
import logging

from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    UserRepository,
    SubscriptionPlanRepository,
    UsageLogRepository,
    ProblemRepository
)
from api.serializers import (
    UserSerializer,
    SubscriptionPlanSerializer,
    ProblemSerializer
)

logger = logging.getLogger(__name__)


class IsAdminUser:
    """Permission class to check if user is admin"""
    def has_permission(self, request, view):
        try:
            return request.user and request.user.is_authenticated and request.user.is_admin()
        except (AttributeError, Exception):
            # is_admin() method doesn't exist or failed
            return False


class UserManagementView(APIView):
    """User management view for admins - DynamoDB implementation"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all users with their subscription plans and usage stats"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repositories
            table = DynamoDBClient.get_table()
            user_repo = UserRepository(table)
            plan_repo = SubscriptionPlanRepository(table)

            # Get all active users
            users = user_repo.list_active_users()

            # Filter by subscription plan if provided
            plan_id = request.query_params.get('plan_id')
            if plan_id:
                users = [u for u in users if u.get('subscription_plan_id') == int(plan_id)]

            # Search by email or name
            search = request.query_params.get('search')
            if search:
                search_lower = search.lower()
                users = [
                    u for u in users
                    if search_lower in u.get('email', '').lower() or
                       search_lower in u.get('name', '').lower()
                ]

            # Transform DynamoDB users to serializer format
            users_data = []
            for user in users:
                # Get subscription plan details
                plan_data = None
                if user.get('subscription_plan_id'):
                    plan = plan_repo.get_plan(user['subscription_plan_id'])
                    if plan:
                        plan_data = {
                            'id': plan['id'],
                            'name': plan['name'],
                            'max_hints_per_day': plan.get('max_hints_per_day', 0),
                            'max_executions_per_day': plan.get('max_executions_per_day', 0)
                        }

                users_data.append({
                    'id': user.get('user_id'),  # DynamoDB uses 'user_id' not 'id'
                    'email': user['email'],
                    'name': user.get('name', ''),
                    'role': 'admin' if user.get('is_staff') else 'user',
                    'is_active': user.get('is_active', True),
                    'is_admin': user.get('is_staff', False),
                    'subscription_plan': plan_data,
                    'subscription_plan_name': plan_data['name'] if plan_data else None,
                    'created_at': datetime.fromtimestamp(user.get('created_at', 0)).isoformat() if user.get('created_at') else None
                })

            return Response({'users': users_data})

        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return Response(
                {'error': f'Failed to fetch users: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, user_id=None):
        """Update user's subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize repositories
            table = DynamoDBClient.get_table()
            user_repo = UserRepository(table)
            plan_repo = SubscriptionPlanRepository(table)

            # Get user
            user = user_repo.get_user_by_id(int(user_id))
            if not user:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update subscription plan if provided
            plan_id = request.data.get('subscription_plan')
            if plan_id:
                # Verify plan exists
                plan = plan_repo.get_plan(int(plan_id))
                if not plan:
                    return Response(
                        {'error': 'Subscription plan not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Update user
                user_repo.update_user(
                    user_id=int(user_id),
                    updates={'subscription_plan_id': int(plan_id)}
                )

                # Get updated user with plan details
                user = user_repo.get_user_by_id(int(user_id))
                plan_data = {
                    'id': plan['id'],
                    'name': plan['name'],
                    'max_hints_per_day': plan.get('max_hints_per_day', 0),
                    'max_executions_per_day': plan.get('max_executions_per_day', 0)
                }
            else:
                plan_data = None
                if user.get('subscription_plan_id'):
                    plan = plan_repo.get_plan(user['subscription_plan_id'])
                    if plan:
                        plan_data = {
                            'id': plan['id'],
                            'name': plan['name'],
                            'max_hints_per_day': plan.get('max_hints_per_day', 0),
                            'max_executions_per_day': plan.get('max_executions_per_day', 0)
                        }

            # Return updated user
            user_data = {
                'id': user['id'],
                'email': user['email'],
                'name': user.get('name', ''),
                'role': user.get('role', 'user'),
                'is_active': user.get('is_active', True),
                'subscription_plan': plan_data,
                'created_at': datetime.fromtimestamp(user.get('created_at', 0)).isoformat() if user.get('created_at') else None
            }

            return Response(user_data)

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return Response(
                {'error': f'Failed to update user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, user_id=None):
        """Update user's subscription plan (alias for patch)"""
        return self.patch(request, user_id)


class SubscriptionPlanManagementView(APIView):
    """Subscription plan management view for admins - DynamoDB implementation"""
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id=None):
        """List all subscription plans or get a specific plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repositories
            table = DynamoDBClient.get_table()
            plan_repo = SubscriptionPlanRepository(table)
            user_repo = UserRepository(table)

            if plan_id:
                plan = plan_repo.get_plan(int(plan_id))
                if not plan:
                    return Response(
                        {'error': 'Subscription plan not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Count users with this plan
                users = user_repo.list_active_users()
                user_count = sum(1 for u in users if u.get('subscription_plan_id') == int(plan_id))

                plan_data = {
                    'id': plan['id'],
                    'name': plan['name'],
                    'description': plan.get('description', ''),
                    'max_hints_per_day': plan.get('max_hints_per_day', 0),
                    'max_executions_per_day': plan.get('max_executions_per_day', 0),
                    'max_problems': plan.get('max_problems', -1),
                    'can_view_all_problems': plan.get('can_view_all_problems', True),
                    'can_register_problems': plan.get('can_register_problems', False),
                    'price': plan.get('price', 0),
                    'is_active': plan.get('is_active', True),
                    'user_count': user_count
                }

                return Response(plan_data)

            # Get all plans
            plans = plan_repo.list_plans()
            users = user_repo.list_active_users()

            # Count users per plan
            plan_user_counts = {}
            for user in users:
                plan_id_key = user.get('subscription_plan_id')
                if plan_id_key:
                    plan_user_counts[plan_id_key] = plan_user_counts.get(plan_id_key, 0) + 1

            plans_data = []
            for plan in plans:
                plans_data.append({
                    'id': plan['id'],
                    'name': plan['name'],
                    'description': plan.get('description', ''),
                    'max_hints_per_day': plan.get('max_hints_per_day', 0),
                    'max_executions_per_day': plan.get('max_executions_per_day', 0),
                    'max_problems': plan.get('max_problems', -1),
                    'can_view_all_problems': plan.get('can_view_all_problems', True),
                    'can_register_problems': plan.get('can_register_problems', False),
                    'price': plan.get('price', 0),
                    'is_active': plan.get('is_active', True),
                    'user_count': plan_user_counts.get(plan['id'], 0)
                })

            return Response({'plans': plans_data})

        except Exception as e:
            logger.error(f"Error fetching plans: {e}")
            return Response(
                {'error': f'Failed to fetch plans: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create a new subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            table = DynamoDBClient.get_table()
            plan_repo = SubscriptionPlanRepository(table)

            # Validate required fields
            required_fields = ['name', 'max_hints_per_day', 'max_executions_per_day']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {'error': f'Missing required field: {field}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Generate new plan ID (get max ID + 1)
            plans = plan_repo.list_plans()
            max_id = max([p['id'] for p in plans], default=0)
            new_plan_id = max_id + 1

            # Create plan data
            plan_data = {
                'id': new_plan_id,
                'name': request.data['name'],
                'max_hints_per_day': int(request.data['max_hints_per_day']),
                'max_executions_per_day': int(request.data['max_executions_per_day']),
                'price': float(request.data.get('price', 0)),
                'is_active': request.data.get('is_active', True)
            }

            # Create plan
            plan_repo.create_plan(plan_data)

            return Response(plan_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return Response(
                {'error': f'Failed to create plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, plan_id):
        """Update a subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            table = DynamoDBClient.get_table()
            plan_repo = SubscriptionPlanRepository(table)

            # Get existing plan
            plan = plan_repo.get_plan(int(plan_id))
            if not plan:
                return Response(
                    {'error': 'Subscription plan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Build updates dict
            updates = {}
            if 'name' in request.data:
                updates['name'] = request.data['name']
            if 'description' in request.data:
                updates['description'] = request.data['description']
            if 'max_hints_per_day' in request.data:
                updates['max_hints_per_day'] = int(request.data['max_hints_per_day'])
            if 'max_executions_per_day' in request.data:
                updates['max_executions_per_day'] = int(request.data['max_executions_per_day'])
            if 'max_problems' in request.data:
                updates['max_problems'] = int(request.data['max_problems'])
            if 'can_view_all_problems' in request.data:
                updates['can_view_all_problems'] = bool(request.data['can_view_all_problems'])
            if 'can_register_problems' in request.data:
                updates['can_register_problems'] = bool(request.data['can_register_problems'])
            if 'price' in request.data:
                updates['price'] = float(request.data['price'])
            if 'is_active' in request.data:
                updates['is_active'] = request.data['is_active']

            # Update plan
            updated_plan = plan_repo.update_plan(int(plan_id), updates)

            return Response(updated_plan)

        except Exception as e:
            logger.error(f"Error updating plan: {e}")
            return Response(
                {'error': f'Failed to update plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, plan_id):
        """Delete a subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repositories
            table = DynamoDBClient.get_table()
            plan_repo = SubscriptionPlanRepository(table)
            user_repo = UserRepository(table)

            # Get plan
            plan = plan_repo.get_plan(int(plan_id))
            if not plan:
                return Response(
                    {'error': 'Subscription plan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if any users have this plan
            users = user_repo.list_active_users()
            user_count = sum(1 for u in users if u.get('subscription_plan_id') == int(plan_id))

            if user_count > 0:
                return Response(
                    {
                        'error': f'Cannot delete plan with {user_count} active users. '
                                f'Please reassign users to another plan first.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Delete plan
            plan_repo.delete_plan(int(plan_id))

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting plan: {e}")
            return Response(
                {'error': f'Failed to delete plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsageStatsView(APIView):
    """Usage statistics view for admins - DynamoDB implementation with caching"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage statistics with aggressive caching"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get date range from query params
        days = int(request.query_params.get('days', 7))

        # Create cache key based on parameters
        cache_key = f"admin_usage_stats:days_{days}"

        # Try to get from cache (15 minute TTL)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data, status=status.HTTP_200_OK)

        logger.debug(f"Cache MISS: {cache_key} - Computing stats...")

        try:
            # Initialize repositories
            table = DynamoDBClient.get_table()
            user_repo = UserRepository(table)
            problem_repo = ProblemRepository(table)
            usage_repo = UsageLogRepository(table)
            plan_repo = SubscriptionPlanRepository(table)

            # Overall stats
            active_users = user_repo.list_active_users()
            total_users = len(active_users)

            # Count total problems (completed only) - uses efficient GSI3 Query now
            problems, _ = problem_repo.list_completed_problems(limit=10000)
            total_problems = len(problems)

            # Usage stats for the period (using date range)
            # Get usage logs for all users in the period
            from datetime import datetime
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            hints_count = 0
            executions_count = 0
            user_activity = {}  # {user_id: count}

            # Aggregate usage across all users
            for user in active_users:
                user_id = user['id']

                # Get usage logs for this user in the date range
                user_logs = usage_repo.list_user_usage(
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=1000
                )

                for log in user_logs:
                    action = log.get('action')
                    if action == 'hint':
                        hints_count += 1
                    elif action == 'execution':
                        executions_count += 1

                    # Count activity per user
                    user_activity[user_id] = user_activity.get(user_id, 0) + 1

            # Get top 10 users by activity
            sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]

            top_users_data = []
            for user_id, activity_count in sorted_users:
                # Find user data
                user = next((u for u in active_users if u['id'] == user_id), None)
                if user:
                    plan_name = 'None'
                    if user.get('subscription_plan_id'):
                        plan = plan_repo.get_plan(user['subscription_plan_id'])
                        if plan:
                            plan_name = plan['name']

                    top_users_data.append({
                        'email': user['email'],
                        'name': user.get('name', ''),
                        'activity_count': activity_count,
                        'subscription_plan': plan_name
                    })

            # Subscription plan distribution
            plan_counts = {}
            for user in active_users:
                plan_id = user.get('subscription_plan_id')
                if plan_id:
                    plan_counts[plan_id] = plan_counts.get(plan_id, 0) + 1

            plan_distribution = []
            plans = plan_repo.list_plans()
            for plan in plans:
                plan_distribution.append({
                    'name': plan['name'],
                    'user_count': plan_counts.get(plan['id'], 0)
                })

            response_data = {
                'period_days': days,
                'total_users': total_users,
                'total_problems': total_problems,
                'hints_count': hints_count,
                'executions_count': executions_count,
                'top_users': top_users_data,
                'plan_distribution': plan_distribution
            }

            # Cache the result for 15 minutes (900 seconds)
            cache.set(cache_key, response_data, 900)
            logger.debug(f"Cached: {cache_key} (TTL: 900s)")

            return Response(response_data)

        except Exception as e:
            logger.error(f"Error fetching usage stats: {e}")
            return Response(
                {'error': f'Failed to fetch usage stats: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProblemReviewView(APIView):
    """Problem review management for admins - DynamoDB implementation"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List problems that need review
        Query params:
            - needs_review: filter by needs_review status (true/false)
            - verified: filter by verified_by_admin status (true/false)
            - platform: filter by platform
            - limit: number of results (default 50)
        """
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Initialize repository
            table = DynamoDBClient.get_table()
            problem_repo = ProblemRepository(table)

            # Get all problems (both drafts and completed)
            all_problems = []
            all_problems.extend(problem_repo.list_draft_problems(limit=1000))
            all_problems.extend(problem_repo.list_completed_problems(limit=1000))

            # Filter by review status
            needs_review = request.query_params.get('needs_review')
            if needs_review is not None:
                needs_review_bool = needs_review.lower() == 'true'
                all_problems = [
                    p for p in all_problems
                    if p.get('needs_review', False) == needs_review_bool
                ]

            # Filter by verification status
            verified = request.query_params.get('verified')
            if verified is not None:
                verified_bool = verified.lower() == 'true'
                all_problems = [
                    p for p in all_problems
                    if p.get('verified_by_admin', False) == verified_bool
                ]

            # Filter by platform
            platform = request.query_params.get('platform')
            if platform:
                all_problems = [p for p in all_problems if p.get('platform') == platform]

            # Limit results
            limit = int(request.query_params.get('limit', 50))
            all_problems = all_problems[:limit]

            # Transform to response format with test case count
            problems_data = []
            for problem in all_problems:
                # Get test cases count
                testcases = problem_repo.get_testcases(
                    platform=problem['platform'],
                    problem_id=problem['problem_id']
                )

                problems_data.append({
                    'platform': problem['platform'],
                    'problem_id': problem['problem_id'],
                    'title': problem['title'],
                    'problem_url': problem.get('problem_url', ''),
                    'tags': problem.get('tags', []),
                    'language': problem.get('language', ''),
                    'is_completed': problem.get('is_completed', False),
                    'needs_review': problem.get('needs_review', False),
                    'verified_by_admin': problem.get('verified_by_admin', False),
                    'review_notes': problem.get('review_notes'),
                    'reviewed_at': problem.get('reviewed_at'),
                    'test_case_count': len(testcases),
                    'created_at': problem.get('created_at')
                })

            return Response({
                'problems': problems_data,
                'count': len(problems_data)
            })

        except Exception as e:
            logger.error(f"Error fetching problems for review: {e}")
            return Response(
                {'error': f'Failed to fetch problems: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, problem_id=None, platform=None, problem_identifier=None):
        """
        Update problem review status
        Body params:
            - needs_review: boolean
            - review_notes: string
            - verified_by_admin: boolean
        """
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Support both legacy (problem_id) and new (platform/problem_identifier) formats
        if not platform or not problem_identifier:
            return Response(
                {'error': 'Platform and problem_identifier required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize repository
            table = DynamoDBClient.get_table()
            problem_repo = ProblemRepository(table)

            # Get problem
            problem = problem_repo.get_problem(
                platform=platform,
                problem_id=problem_identifier
            )

            if not problem:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Build updates dict
            updates = {}
            if 'needs_review' in request.data:
                updates['needs_review'] = request.data['needs_review']

            if 'review_notes' in request.data:
                updates['review_notes'] = request.data['review_notes']

            if 'verified_by_admin' in request.data:
                updates['verified_by_admin'] = request.data['verified_by_admin']
                if request.data['verified_by_admin']:
                    updates['reviewed_at'] = int(timezone.now().timestamp())

            # Update problem
            updated_problem = problem_repo.update_problem(
                platform=platform,
                problem_id=problem_identifier,
                updates=updates
            )

            # Get test cases count
            testcases = problem_repo.get_testcases(
                platform=platform,
                problem_id=problem_identifier
            )

            # Return updated problem
            problem_data = {
                'platform': updated_problem['platform'],
                'problem_id': updated_problem['problem_id'],
                'title': updated_problem['title'],
                'problem_url': updated_problem.get('problem_url', ''),
                'tags': updated_problem.get('tags', []),
                'language': updated_problem.get('language', ''),
                'is_completed': updated_problem.get('is_completed', False),
                'needs_review': updated_problem.get('needs_review', False),
                'verified_by_admin': updated_problem.get('verified_by_admin', False),
                'review_notes': updated_problem.get('review_notes'),
                'reviewed_at': updated_problem.get('reviewed_at'),
                'test_case_count': len(testcases),
                'created_at': updated_problem.get('created_at')
            }

            return Response(problem_data)

        except Exception as e:
            logger.error(f"Error updating problem review: {e}")
            return Response(
                {'error': f'Failed to update problem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, problem_id=None, platform=None, problem_identifier=None):
        """Alias for patch"""
        return self.patch(request, problem_id, platform, problem_identifier)
