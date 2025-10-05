"""API URL Configuration"""
from django.urls import path
from .views import (
    GoogleLoginView,
    TokenRefreshView,
    LogoutView,
    ProblemListView,
    ProblemDetailView,
    ProblemDraftsView,
    ProblemRegisteredView,
    ExecuteCodeView,
    SearchHistoryListView,
    SearchHistoryDetailView,
    RegisterProblemView,
    GenerateTestCasesView,
    ExecuteTestCasesView,
    DraftProblemsView,
    SaveProblemView,
    JobListView,
    JobDetailView,
)

urlpatterns = [
    # Authentication
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Problems
    path('problems/', ProblemListView.as_view(), name='problem-list'),
    path('problems/drafts/', ProblemDraftsView.as_view(), name='problem-drafts'),
    path('problems/registered/', ProblemRegisteredView.as_view(), name='problem-registered'),
    path('problems/<int:problem_id>/', ProblemDetailView.as_view(), name='problem-detail'),
    path('problems/<str:platform>/<str:problem_identifier>/', ProblemDetailView.as_view(), name='problem-detail-by-platform'),

    # Code Execution
    path('execute/', ExecuteCodeView.as_view(), name='execute-code'),

    # Search History
    path('history/', SearchHistoryListView.as_view(), name='history-list'),
    path('history/<int:history_id>/', SearchHistoryDetailView.as_view(), name='history-detail'),

    # Problem Registration
    path('register/problem/', RegisterProblemView.as_view(), name='register-problem'),
    path('register/generate-test-cases/', GenerateTestCasesView.as_view(), name='generate-test-cases'),
    path('register/execute-test-cases/', ExecuteTestCasesView.as_view(), name='execute-test-cases'),
    path('register/drafts/', DraftProblemsView.as_view(), name='draft-problems'),
    path('register/save/', SaveProblemView.as_view(), name='save-problem'),

    # Script Generation Jobs
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<int:job_id>/', JobDetailView.as_view(), name='job-detail'),
]
