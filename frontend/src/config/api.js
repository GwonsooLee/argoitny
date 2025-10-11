/**
 * API Configuration
 *
 * Environment-based API URL configuration:
 * - Development: Uses VITE_API_URL from .env.development (http://localhost:8000/api)
 * - Production: Uses VITE_API_URL from .env.production (https://api.testcase.run/api)
 * - Fallback: http://localhost:8000/api if no environment variable is set
 */

// API Base URL - determined by environment
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Environment info
export const ENV = import.meta.env.VITE_ENV || import.meta.env.MODE;
export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication
  googleLogin: '/auth/google/',
  tokenRefresh: '/auth/refresh/',
  logout: '/auth/logout/',
  availablePlans: '/auth/plans/',

  // Problems
  problems: '/problems/',
  problemDetail: (id) => `/problems/${id}/`,
  problemDetailByPlatform: (platform, problemId) => `/problems/${platform}/${problemId}/`,
  problemDrafts: '/problems/drafts/',
  problemRegistered: '/problems/registered/',

  // Code Execution
  execute: '/execute/',
  // taskStatus: REMOVED - Celery result backend disabled, task status no longer available

  // Search History
  history: '/history/',
  historyDetail: (id) => `/history/${id}/`,

  // Problem Registration
  registerProblem: '/register/problem/',
  generateTestCases: '/register/generate-test-cases/',
  executeTestCases: '/register/execute-test-cases/',
  drafts: '/register/drafts/',
  saveDraft: '/register/save/',
  extractProblemInfo: '/register/extract-problem-info/',

  // Script Generation Jobs
  jobs: '/register/jobs/',
  jobDetail: (id) => `/register/jobs/${id}/`,
  jobRetry: (id) => `/register/jobs/${id}/retry/`,
  jobProgress: (id, jobType = 'extraction') => `/register/jobs/${id}/progress/?job_type=${jobType}`,

  // Hints
  requestHints: (executionId) => `/history/${executionId}/hints/generate/`,
  getHints: (executionId) => `/history/${executionId}/hints/`,

  // Account
  accountStats: '/account/stats/',
  updatePlan: '/account/plan/',
  planUsage: '/account/plan-usage/',
  submitConsents: '/account/consents/',
  getConsents: '/account/consents/status/',

  // Admin
  adminUsers: '/admin/users/',
  adminUserDetail: (userId) => `/admin/users/${userId}/`,
  adminPlans: '/admin/plans/',
  adminPlanDetail: (planId) => `/admin/plans/${planId}/`,
  adminUsageStats: '/admin/usage-stats/',

  // Legal Documents
  legal: '/legal',
  legalAll: '/legal/all/',
  legalTerms: '/legal/terms/',
  legalPrivacy: '/legal/privacy/',
  legalVersions: (docType) => `/legal/${docType}/versions/`,
  legalVersion: (docType, version) => `/legal/${docType}/versions/${version}/`,
};

/**
 * Build full API URL
 */
export const buildApiUrl = (endpoint) => {
  return `${API_BASE_URL}${endpoint}`;
};
