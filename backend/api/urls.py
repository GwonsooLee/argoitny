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
    SaveTestCaseInputsView,
    GenerateOutputsView,
    CheckTaskStatusView,
    ToggleCompletionView,
    JobListView,
    JobDetailView,
)
from .views.account import AccountStatsView
from .views.health import health_check, readiness_check, liveness_check

urlpatterns = [
    # Health Checks
    path('health/', health_check, name='health-check'),
    path('health/ready/', readiness_check, name='readiness-check'),
    path('health/live/', liveness_check, name='liveness-check'),

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
    path('register/', RegisterProblemView.as_view(), name='register-problem-short'),  # Alias for tests
    path('register/problem/', RegisterProblemView.as_view(), name='register-problem'),
    path('register/generate-test-cases/', GenerateTestCasesView.as_view(), name='generate-test-cases'),
    path('register/execute-test-cases/', ExecuteTestCasesView.as_view(), name='execute-test-cases'),
    path('register/drafts/', DraftProblemsView.as_view(), name='draft-problems'),
    path('register/save/', SaveProblemView.as_view(), name='save-problem'),
    path('register/save-test-inputs/', SaveTestCaseInputsView.as_view(), name='save-test-inputs'),
    path('register/generate-outputs/', GenerateOutputsView.as_view(), name='generate-outputs'),
    path('register/toggle-completion/', ToggleCompletionView.as_view(), name='register-toggle-completion'),

    # Script Generation Jobs
    path('register/jobs/', JobListView.as_view(), name='register-job-list'),
    path('register/jobs/<int:job_id>/', JobDetailView.as_view(), name='register-job-detail'),

    # Task Status
    path('register/task-status/<str:task_id>/', CheckTaskStatusView.as_view(), name='register-task-status'),

    # Toggle Completion
    path('problems/toggle-completion/', ToggleCompletionView.as_view(), name='toggle-completion'),

    # Account
    path('account/stats/', AccountStatsView.as_view(), name='account-stats'),
]
