"""Account Views"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count, Q
from ..models import SearchHistory


class AccountStatsView(APIView):
    """Get user account statistics"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get user's test execution statistics

        Returns:
            {
                "total_executions": 100,
                "by_platform": {
                    "baekjoon": 60,
                    "codeforces": 40
                },
                "by_language": {
                    "python": 70,
                    "cpp": 20,
                    "java": 10
                },
                "total_problems": 25,
                "passed_executions": 80,
                "failed_executions": 20
            }
        """
        user = request.user

        # Get all user's search history
        user_history = SearchHistory.objects.filter(user=user)

        # Total executions
        total_executions = user_history.count()

        # Group by platform
        by_platform = {}
        platform_stats = user_history.values('platform').annotate(count=Count('id'))
        for stat in platform_stats:
            by_platform[stat['platform']] = stat['count']

        # Group by language
        by_language = {}
        language_stats = user_history.values('language').annotate(count=Count('id'))
        for stat in language_stats:
            by_language[stat['language']] = stat['count']

        # Total unique problems
        total_problems = user_history.values('problem').distinct().count()

        # Passed vs Failed
        passed_executions = user_history.filter(failed_count=0).count()
        failed_executions = user_history.filter(failed_count__gt=0).count()

        return Response({
            'total_executions': total_executions,
            'by_platform': by_platform,
            'by_language': by_language,
            'total_problems': total_problems,
            'passed_executions': passed_executions,
            'failed_executions': failed_executions
        }, status=status.HTTP_200_OK)
