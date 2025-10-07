"""Admin-only views"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from api.models import User, SubscriptionPlan, UsageLog, Problem, TestCase
from api.serializers import (
    UserManagementSerializer,
    SubscriptionPlanSerializer,
    UsageLogSerializer,
    ProblemSerializer
)


class IsAdminUser:
    """Permission class to check if user is admin"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class UserManagementView(APIView):
    """User management view for admins"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all users with their subscription plans and usage stats"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        users = User.objects.select_related('subscription_plan').filter(is_active=True)

        # Filter by subscription plan if provided
        plan_id = request.query_params.get('plan_id')
        if plan_id:
            users = users.filter(subscription_plan_id=plan_id)

        # Search by email or name
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                Q(email__icontains=search) | Q(name__icontains=search)
            )

        serializer = UserManagementSerializer(users, many=True)
        return Response({'users': serializer.data})

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
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        plan_id = request.data.get('subscription_plan')
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id)
                user.subscription_plan = plan
                user.save()
            except SubscriptionPlan.DoesNotExist:
                return Response(
                    {'error': 'Subscription plan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = UserManagementSerializer(user)
        return Response(serializer.data)

    def put(self, request, user_id=None):
        """Update user's subscription plan (alias for patch)"""
        return self.patch(request, user_id)


class SubscriptionPlanManagementView(APIView):
    """Subscription plan management view for admins"""
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id=None):
        """List all subscription plans or get a specific plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        if plan_id:
            try:
                plan = SubscriptionPlan.objects.annotate(
                    user_count=Count('users')
                ).get(id=plan_id)
                serializer = SubscriptionPlanSerializer(plan)
                return Response(serializer.data)
            except SubscriptionPlan.DoesNotExist:
                return Response(
                    {'error': 'Subscription plan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        plans = SubscriptionPlan.objects.annotate(
            user_count=Count('users')
        ).all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response({'plans': serializer.data})

    def post(self, request):
        """Create a new subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SubscriptionPlanSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, plan_id):
        """Update a subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Subscription plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, plan_id):
        """Delete a subscription plan"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)

            # Check if any users have this plan
            user_count = plan.users.count()
            if user_count > 0:
                return Response(
                    {
                        'error': f'Cannot delete plan with {user_count} active users. '
                                f'Please reassign users to another plan first.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            plan.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Subscription plan not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UsageStatsView(APIView):
    """Usage statistics view for admins"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage statistics"""
        if not request.user.is_admin():
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get date range from query params
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        # Overall stats
        total_users = User.objects.filter(is_active=True).count()
        total_problems = Problem.objects.filter(is_deleted=False).count()

        # Usage stats for the period
        hints_count = UsageLog.objects.filter(
            action='hint',
            created_at__gte=start_date
        ).count()

        executions_count = UsageLog.objects.filter(
            action='execution',
            created_at__gte=start_date
        ).count()

        # Top users by activity
        top_users = User.objects.filter(
            is_active=True,
            usage_logs__created_at__gte=start_date
        ).annotate(
            activity_count=Count('usage_logs')
        ).order_by('-activity_count')[:10]

        top_users_data = [
            {
                'email': user.email,
                'name': user.name,
                'activity_count': user.activity_count,
                'subscription_plan': user.subscription_plan.name if user.subscription_plan else 'None'
            }
            for user in top_users
        ]

        # Subscription plan distribution
        plan_distribution = SubscriptionPlan.objects.annotate(
            user_count=Count('users', filter=Q(users__is_active=True))
        ).values('name', 'user_count')

        return Response({
            'period_days': days,
            'total_users': total_users,
            'total_problems': total_problems,
            'hints_count': hints_count,
            'executions_count': executions_count,
            'top_users': top_users_data,
            'plan_distribution': list(plan_distribution)
        })


class ProblemReviewView(APIView):
    """Problem review management for admins"""
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

        problems = Problem.objects.active().prefetch_related('test_cases')

        # Filter by review status
        needs_review = request.query_params.get('needs_review')
        if needs_review is not None:
            needs_review_bool = needs_review.lower() == 'true'
            problems = problems.filter(needs_review=needs_review_bool)

        # Filter by verification status
        verified = request.query_params.get('verified')
        if verified is not None:
            verified_bool = verified.lower() == 'true'
            problems = problems.filter(verified_by_admin=verified_bool)

        # Filter by platform
        platform = request.query_params.get('platform')
        if platform:
            problems = problems.filter(platform=platform)

        # Limit results
        limit = int(request.query_params.get('limit', 50))
        problems = problems[:limit]

        # Annotate with test case count
        problems = problems.annotate(test_case_count_annotated=Count('test_cases'))

        serializer = ProblemSerializer(problems, many=True)
        return Response({
            'problems': serializer.data,
            'count': len(serializer.data)
        })

    def patch(self, request, problem_id=None):
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

        if not problem_id:
            return Response(
                {'error': 'Problem ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            problem = Problem.objects.prefetch_related('test_cases').get(
                id=problem_id,
                is_deleted=False
            )
        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update review fields
        if 'needs_review' in request.data:
            problem.needs_review = request.data['needs_review']

        if 'review_notes' in request.data:
            problem.review_notes = request.data['review_notes']

        if 'verified_by_admin' in request.data:
            problem.verified_by_admin = request.data['verified_by_admin']
            if request.data['verified_by_admin']:
                problem.reviewed_at = timezone.now()

        problem.save()

        # Return updated problem
        serializer = ProblemSerializer(problem)
        return Response(serializer.data)

    def put(self, request, problem_id=None):
        """Alias for patch"""
        return self.patch(request, problem_id)
