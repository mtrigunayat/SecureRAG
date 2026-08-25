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

export interface Department {
  id: number;
  name: string;
  description: string | null;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  department: Department;
}
