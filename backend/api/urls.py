"""API URL Configuration"""
from django.urls import path
from .views import (
    GoogleLoginView,
    TokenRefreshView,
    LogoutView,
    AvailablePlansView,
    ProblemListView,
    ProblemDetailView,
    ProblemDraftsView,
    ProblemRegisteredView,
    ExecuteCodeView,
    SearchHistoryListView,
    SearchHistoryDetailView,
    GenerateHintsView,
    GetHintsView,
    RegisterProblemView,
    GenerateTestCasesView,
    ExecuteTestCasesView,
    DraftProblemsView,
    SaveProblemView,
    SaveTestCaseInputsView,
    GenerateOutputsView,
    ToggleCompletionView,
    JobListView,
    JobDetailView,
    ExtractProblemInfoView,
    RetryExtractionView,
    JobProgressHistoryView,
    RegenerateSolutionView,
    GetTestCasesView,
)
from .views.account import UpdatePlanView, PlanUsageView, UserProfileView
from .views.health import health_check, readiness_check, liveness_check
from .views.admin import (
    UserManagementView,
    SubscriptionPlanManagementView,
    UsageStatsView,
    ProblemReviewView
)
from .views.legal import (
    get_active_legal_document,
    get_legal_document_version,
    list_legal_document_versions,
    get_all_active_documents
)

urlpatterns = [
    # Health Checks
    path('health/', health_check, name='health-check'),
    path('health/ready/', readiness_check, name='readiness-check'),
    path('health/live/', liveness_check, name='liveness-check'),

    # Authentication
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/plans/', AvailablePlansView.as_view(), name='available-plans'),

    # Problems
    path('problems/', ProblemListView.as_view(), name='problem-list'),
    path('problems/drafts/', ProblemDraftsView.as_view(), name='problem-drafts'),
    path('problems/registered/', ProblemRegisteredView.as_view(), name='problem-registered'),
    path('problems/<int:problem_id>/', ProblemDetailView.as_view(), name='problem-detail'),
    path('problems/<str:platform>/<str:problem_identifier>/', ProblemDetailView.as_view(), name='problem-detail-by-platform'),
    path('problems/<str:platform>/<str:problem_id>/testcases/', GetTestCasesView.as_view(), name='get-testcases'),

    # Code Execution
    path('execute/', ExecuteCodeView.as_view(), name='execute-code'),

    # Search History
    path('history/', SearchHistoryListView.as_view(), name='history-list'),
    path('history/<int:history_id>/', SearchHistoryDetailView.as_view(), name='history-detail'),
    path('history/<int:history_id>/hints/', GetHintsView.as_view(), name='get-hints'),
    path('history/<int:history_id>/hints/generate/', GenerateHintsView.as_view(), name='generate-hints'),

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

    # Script Generation Jobs (UUID-based job IDs)
    path('register/jobs/', JobListView.as_view(), name='register-job-list'),
    path('register/jobs/<str:job_id>/', JobDetailView.as_view(), name='register-job-detail'),
    path('register/jobs/<str:job_id>/retry/', RetryExtractionView.as_view(), name='register-job-retry'),
    path('register/jobs/<str:job_id>/progress/', JobProgressHistoryView.as_view(), name='register-job-progress'),

    # Extract Problem Info
    path('register/extract-problem-info/', ExtractProblemInfoView.as_view(), name='extract-problem-info'),

    # Regenerate Solution
    path('register/problems/<str:platform>/<str:problem_id>/regenerate-solution/', RegenerateSolutionView.as_view(), name='regenerate-solution'),

    # Toggle Completion
    path('problems/toggle-completion/', ToggleCompletionView.as_view(), name='toggle-completion'),

    # Account
    path('account/me/', UserProfileView.as_view(), name='user-profile'),
    path('account/plan/', UpdatePlanView.as_view(), name='update-plan'),
    path('account/plan-usage/', PlanUsageView.as_view(), name='plan-usage'),

    # Admin
    path('admin/users/', UserManagementView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', UserManagementView.as_view(), name='admin-user-detail'),
    path('admin/plans/', SubscriptionPlanManagementView.as_view(), name='admin-plans'),
    path('admin/plans/<int:plan_id>/', SubscriptionPlanManagementView.as_view(), name='admin-plan-detail'),
    path('admin/usage-stats/', UsageStatsView.as_view(), name='admin-usage-stats'),
    path('admin/problems/review/', ProblemReviewView.as_view(), name='admin-problem-review'),
    path('admin/problems/review/<int:problem_id>/', ProblemReviewView.as_view(), name='admin-problem-review-detail'),

    # Legal Documents
    path('legal/all/', get_all_active_documents, name='legal-all-active'),
    path('legal/<str:document_type>/', get_active_legal_document, name='legal-active'),
    path('legal/<str:document_type>/versions/', list_legal_document_versions, name='legal-versions'),
    path('legal/<str:document_type>/versions/<str:version>/', get_legal_document_version, name='legal-version'),
]
