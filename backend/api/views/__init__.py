"""API Views"""
from .auth import GoogleLoginView, TokenRefreshView, LogoutView, AvailablePlansView
from .problems import ProblemListView, ProblemDetailView, ProblemDraftsView, ProblemRegisteredView
from .execute import ExecuteCodeView
from .history import SearchHistoryListView, SearchHistoryDetailView, GenerateHintsView, GetHintsView
from .register import (
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
    GetTestCasesView
)

__all__ = [
    'GoogleLoginView',
    'TokenRefreshView',
    'LogoutView',
    'AvailablePlansView',
    'ProblemListView',
    'ProblemDetailView',
    'ProblemDraftsView',
    'ProblemRegisteredView',
    'ExecuteCodeView',
    'SearchHistoryListView',
    'SearchHistoryDetailView',
    'GenerateHintsView',
    'GetHintsView',
    'RegisterProblemView',
    'GenerateTestCasesView',
    'ExecuteTestCasesView',
    'DraftProblemsView',
    'SaveProblemView',
    'SaveTestCaseInputsView',
    'GenerateOutputsView',
    'ToggleCompletionView',
    'JobListView',
    'JobDetailView',
    'ExtractProblemInfoView',
    'RetryExtractionView',
    'JobProgressHistoryView',
    'RegenerateSolutionView',
    'GetTestCasesView',
]
