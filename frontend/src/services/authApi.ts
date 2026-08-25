/**
 * Authentication API service
 */

import { apiClient } from './apiClient';
import { handleResponse } from '../utils/api';
import type { LoginRequest, LoginResponse } from '../types/auth';

export const authApi = {
  /**
   * Login user with email and password
   * 
   * POST /api/auth/login
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post('/api/auth/login', credentials);
    return handleResponse<LoginResponse>(response as Response);
  },
};
