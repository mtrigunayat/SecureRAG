/**
 * Authentication types
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthError {
  detail: string;
}

export interface User {
  email: string;
  // Add other user fields as needed from backend
}
