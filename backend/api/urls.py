"""API URL Configuration"""
from django.urls import path
from .views import (
    GoogleLoginView,
    TokenRefreshView,
    LogoutView,
    ProblemListView,
    ProblemDetailView,
    ExecuteCodeView,
    SearchHistoryListView,
    SearchHistoryDetailView,
    RegisterProblemView,
    GenerateTestCasesView,
)

urlpatterns = [
    # Authentication
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Problems
    path('problems/', ProblemListView.as_view(), name='problem-list'),
    path('problems/<int:problem_id>/', ProblemDetailView.as_view(), name='problem-detail'),

    # Code Execution
    path('execute/', ExecuteCodeView.as_view(), name='execute-code'),

    # Search History
    path('history/', SearchHistoryListView.as_view(), name='history-list'),
    path('history/<int:history_id>/', SearchHistoryDetailView.as_view(), name='history-detail'),

    # Problem Registration
    path('register/problem/', RegisterProblemView.as_view(), name='register-problem'),
    path('register/generate-test-cases/', GenerateTestCasesView.as_view(), name='generate-test-cases'),
]
