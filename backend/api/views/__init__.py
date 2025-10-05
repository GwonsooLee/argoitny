"""API Views"""
from .auth import GoogleLoginView, TokenRefreshView, LogoutView
from .problems import ProblemListView, ProblemDetailView, ProblemDraftsView, ProblemRegisteredView
from .execute import ExecuteCodeView
from .history import SearchHistoryListView, SearchHistoryDetailView
from .register import (
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
    JobDetailView
)

__all__ = [
    'GoogleLoginView',
    'TokenRefreshView',
    'LogoutView',
    'ProblemListView',
    'ProblemDetailView',
    'ProblemDraftsView',
    'ProblemRegisteredView',
    'ExecuteCodeView',
    'SearchHistoryListView',
    'SearchHistoryDetailView',
    'RegisterProblemView',
    'GenerateTestCasesView',
    'ExecuteTestCasesView',
    'DraftProblemsView',
    'SaveProblemView',
    'SaveTestCaseInputsView',
    'GenerateOutputsView',
    'CheckTaskStatusView',
    'ToggleCompletionView',
    'JobListView',
    'JobDetailView',
]
