/**
 * API Client with authentication and token refresh
 */
import { buildApiUrl } from '../config/api';
import { getAccessToken, getRefreshToken, saveTokens, removeTokens } from './auth';

/**
 * Refresh access token
 */
const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await fetch(buildApiUrl('/auth/refresh/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh: refreshToken }),
  });

  if (!response.ok) {
    removeTokens();
    throw new Error('Failed to refresh token');
  }

  const data = await response.json();
  saveTokens(data.access, data.refresh || refreshToken);
  return data.access;
};

/**
 * API Client with automatic token refresh
 */
export const apiClient = async (endpoint, options = {}) => {
  const { requireAuth = false, ...fetchOptions } = options;

  // Build headers
  const headers = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };

  // Add authentication token if required
  if (requireAuth) {
    const token = getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  // Make request
  let response = await fetch(buildApiUrl(endpoint), {
    ...fetchOptions,
    headers,
  });

  // If 401 and we have a refresh token, try to refresh
  if (response.status === 401 && requireAuth && getRefreshToken()) {
    try {
      const newToken = await refreshAccessToken();
      headers['Authorization'] = `Bearer ${newToken}`;

      // Retry request with new token
      response = await fetch(buildApiUrl(endpoint), {
        ...fetchOptions,
        headers,
      });
    } catch (error) {
      console.error('Failed to refresh token:', error);
      removeTokens();
      throw error;
    }
  }

  return response;
};

/**
 * Convenience methods
 */
export const apiGet = (endpoint, options = {}) => {
  return apiClient(endpoint, { ...options, method: 'GET' });
};

export const apiPost = (endpoint, data, options = {}) => {
  return apiClient(endpoint, {
    ...options,
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const apiPut = (endpoint, data, options = {}) => {
  return apiClient(endpoint, {
    ...options,
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

export const apiDelete = (endpoint, options = {}) => {
  return apiClient(endpoint, { ...options, method: 'DELETE' });
};
