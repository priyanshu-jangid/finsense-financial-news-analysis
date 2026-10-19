/**
 * Authentication utilities and API functions for FinSense frontend.
 * Stores JWT token in localStorage under the key `finsense-token`.
 */
import api from './client';
import type { UserProfile } from '../types';

const TOKEN_KEY = 'finsense-token';

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

export const isLoggedIn = (): boolean => {
  return !!getToken();
};

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const loginUser = async (email: string, password: string): Promise<LoginResponse> => {
  const params = new URLSearchParams();
  params.append('username', email.trim().toLowerCase());
  params.append('password', password);

  const response = await api.post<LoginResponse>('/auth/login', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  if (response.data?.access_token) {
    setToken(response.data.access_token);
  }
  return response.data;
};

export const registerUser = async (email: string, password: string): Promise<UserProfile> => {
  const response = await api.post<UserProfile>('/auth/register', {
    email: email.trim().toLowerCase(),
    password,
  });
  return response.data;
};

export const fetchCurrentUser = async (): Promise<UserProfile> => {
  const response = await api.get<UserProfile>('/auth/me');
  return response.data;
};
