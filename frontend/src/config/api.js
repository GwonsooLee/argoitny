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

// Environment info (useful for debugging)
export const ENV = import.meta.env.VITE_ENV || import.meta.env.MODE;
export const isDevelopment = import.meta.env.DEV;
export const isProduction = import.meta.env.PROD;

// Log configuration in development
if (isDevelopment) {
  console.log('[API Config] Environment:', ENV);
  console.log('[API Config] Base URL:', API_BASE_URL);
  console.log('[API Config] Mode:', import.meta.env.MODE);
}

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
