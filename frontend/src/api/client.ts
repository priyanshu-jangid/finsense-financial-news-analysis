import axios from 'axios';
import { getToken, clearToken } from './auth';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL,
  timeout: 10000,
});

// Request interceptor to add Authorization header
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect if 401 occurs outside login/register and the user was authenticated
    if (error.response?.status === 401) {
      const isAuthEndpoint = error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/register');
      if (!isAuthEndpoint) {
        clearToken();
        const currentPath = window.location.pathname;
        if (currentPath !== '/login' && currentPath !== '/register') {
          // Dispatch custom event so app state updates smoothly
          window.dispatchEvent(new Event('auth-unauthorized'));
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
