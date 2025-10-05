/**
 * API Configuration
 */

// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication
  googleLogin: '/auth/google/',
  tokenRefresh: '/auth/refresh/',
  logout: '/auth/logout/',

  // Problems
  problems: '/problems/',
  problemDetail: (id) => `/problems/${id}/`,
  problemDetailByPlatform: (platform, problemId) => `/problems/${platform}/${problemId}/`,
  problemDrafts: '/problems/drafts/',
  problemRegistered: '/problems/registered/',

  // Code Execution
  execute: '/execute/',

  // Search History
  history: '/history/',
  historyDetail: (id) => `/history/${id}/`,

  // Problem Registration
  registerProblem: '/register/problem/',
  generateTestCases: '/register/generate-test-cases/',
  executeTestCases: '/register/execute-test-cases/',
  drafts: '/register/drafts/',
  saveDraft: '/register/save/',

  // Script Generation Jobs
  jobs: '/jobs/',
  jobDetail: (id) => `/jobs/${id}/`,
};

/**
 * Build full API URL
 */
export const buildApiUrl = (endpoint) => {
  return `${API_BASE_URL}${endpoint}`;
};
