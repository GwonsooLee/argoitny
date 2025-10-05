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
  const { requireAuth = false, timeout = 30000, ...fetchOptions } = options;

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

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    // Make request
    let response = await fetch(buildApiUrl(endpoint), {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // If 401 and we have a refresh token, try to refresh
    if (response.status === 401 && requireAuth && getRefreshToken()) {
      try {
        const newToken = await refreshAccessToken();
        headers['Authorization'] = `Bearer ${newToken}`;

        // Retry request with new token
        const retryController = new AbortController();
        const retryTimeoutId = setTimeout(() => retryController.abort(), timeout);

        response = await fetch(buildApiUrl(endpoint), {
          ...fetchOptions,
          headers,
          signal: retryController.signal,
        });

        clearTimeout(retryTimeoutId);
      } catch (error) {
        console.error('Failed to refresh token:', error);
        removeTokens();
        throw error;
      }
    }

    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
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
