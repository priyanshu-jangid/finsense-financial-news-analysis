import React, { useEffect, useState } from 'react';
import { AuthContext } from './authContextDef';
import {
  getToken,
  clearToken,
  loginUser,
  registerUser,
  fetchCurrentUser,
} from '../api/auth';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const initialToken = getToken();
  const [tokenState, setTokenState] = useState<string | null>(initialToken);
  const [user, setUser] = useState<import('../types').UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!!initialToken);

  useEffect(() => {
    let active = true;

    const init = async () => {
      const currentToken = getToken();
      if (!currentToken) {
        return;
      }
      try {
        const profile = await fetchCurrentUser();
        if (active) setUser(profile);
      } catch {
        if (active) {
          clearToken();
          setTokenState(null);
          setUser(null);
        }
      } finally {
        if (active) setIsLoading(false);
      }
    };

    init();

    const handleUnauthorized = () => {
      clearToken();
      setTokenState(null);
      setUser(null);
    };

    window.addEventListener('auth-unauthorized', handleUnauthorized);
    return () => {
      active = false;
      window.removeEventListener('auth-unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await loginUser(email, password);
      setTokenState(res.access_token);
      const profile = await fetchCurrentUser();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      await registerUser(email, password);
      const res = await loginUser(email, password);
      setTokenState(res.access_token);
      const profile = await fetchCurrentUser();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearToken();
    setTokenState(null);
    setUser(null);
  };

  const refreshUser = async () => {
    const currentToken = getToken();
    if (!currentToken) {
      setUser(null);
      return;
    }
    try {
      const profile = await fetchCurrentUser();
      setUser(profile);
    } catch {
      clearToken();
      setTokenState(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token: tokenState,
        isAuthenticated: !!user && !!tokenState,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
