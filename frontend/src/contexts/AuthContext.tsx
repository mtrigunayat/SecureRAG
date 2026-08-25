/**
 * Authentication Context
 * 
 * Manages authentication state across the application.
 * Stores JWT token in localStorage and fetches user information.
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authApi } from '../services/authApi';
import type { LoginRequest, User } from '../types/auth';

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'auth_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load token from localStorage and fetch user info on mount
  useEffect(() => {
    const loadUserData = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken) {
        setToken(storedToken);
        try {
          const userData = await authApi.getCurrentUser();
          setUser(userData);
        } catch (error) {
          // Token is invalid, clear it
          console.error('Failed to load user data:', error);
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    loadUserData();
  }, []);

  const login = async (credentials: LoginRequest) => {
    const response = await authApi.login(credentials);
    const newToken = response.access_token;
    
    setToken(newToken);
    localStorage.setItem(TOKEN_KEY, newToken);

    // Fetch user information after login
    const userData = await authApi.getCurrentUser();
    setUser(userData);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
  };

  const value: AuthContextType = {
    token,
    user,
    isAuthenticated: !!token,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
