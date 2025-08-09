// API Interceptor for handling authentication errors
// This can be used to automatically handle 401/403 responses across the app

import { isAuthenticationError } from './auth';

// Global error handler for API responses
export function handleApiError(error: any, onAuthError?: () => void): void {
  if (isAuthenticationError(error)) {
    console.warn('Authentication error detected:', error);
    if (onAuthError) {
      onAuthError();
    }
  }
}

// Wrapper for fetch requests with automatic auth error handling
export async function fetchWithAuthHandling(
  url: string,
  options: RequestInit = {},
  onAuthError?: () => void
): Promise<Response> {
  try {
    const response = await fetch(url, {
      credentials: 'include',
      ...options,
    });

    if (!response.ok && (response.status === 401 || response.status === 403)) {
      const error = {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`,
      };
      handleApiError(error, onAuthError);
      throw error;
    }

    return response;
  } catch (error) {
    handleApiError(error, onAuthError);
    throw error;
  }
}

// Example usage in components:
// import { fetchWithAuthHandling } from '../utils/apiInterceptor';
// import { useAuth } from '../context/AuthContext';
//
// const { signOut } = useAuth();
// const response = await fetchWithAuthHandling('/api/some-endpoint', {}, signOut);