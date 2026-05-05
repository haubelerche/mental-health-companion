/**
 * Auth Context
 * Tracks authentication state for WebSocket and other features
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

interface AuthContextType {
  isAuthenticated: boolean;
  accessToken: string | null;
  setAuthenticated: (token: string | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Check if user is authenticated on mount
  useEffect(() => {
    // Simple check: if there's a cookie, assume authenticated
    // The actual token is in an HTTP-only cookie, so we just need to know the auth state
    const checkAuth = async () => {
      try {
        const response = await fetch("/v1/auth/me", {
          credentials: "include",
        });
        setIsAuthenticated(response.ok);
      } catch {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  const setAuthenticated = useCallback((token: string | null) => {
    setAccessToken(token);
    setIsAuthenticated(!!token);
  }, []);

  const logout = useCallback(() => {
    setAccessToken(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        accessToken,
        setAuthenticated,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
