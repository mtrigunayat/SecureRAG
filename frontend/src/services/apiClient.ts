/**
 * Centralized API client
 * 
 * Provides base HTTP methods with authentication support.
 * All API calls should go through this client.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface RequestOptions extends RequestInit {
  token?: string;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add existing headers
  if (fetchOptions.headers) {
    const existingHeaders = fetchOptions.headers as Record<string, string>;
    Object.assign(headers, existingHeaders);
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  return response as unknown as T;
}

export const apiClient = {
  get: <T>(endpoint: string, token?: string): Promise<T> =>
    request<T>(endpoint, { method: 'GET', token }),

  post: <T>(endpoint: string, data?: unknown, token?: string): Promise<T> =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      token,
    }),

  put: <T>(endpoint: string, data?: unknown, token?: string): Promise<T> =>
    request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      token,
    }),

  delete: <T>(endpoint: string, token?: string): Promise<T> =>
    request<T>(endpoint, { method: 'DELETE', token }),
};
