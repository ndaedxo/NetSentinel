import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { User } from '@/services/auth-service';
import { mockUser } from '@/mock';
import { setUserContext, clearUserContext, addBreadcrumb } from '@/utils/sentry';

// Auth context types
interface AuthContextType {
  user: User | null;
  isPending: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  redirectToLogin: () => void;
  exchangeCodeForSessionToken: (code: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock auth provider props
interface AuthProviderProps {
  children: ReactNode;
}

// Auth storage key
const AUTH_STORAGE_KEY = 'netsentinel-auth';

// Get user from localStorage
const getStoredUser = (): User | null => {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const { user, expiresAt } = JSON.parse(stored);
      // Check if session is still valid (24 hours)
      if (Date.now() < expiresAt) {
        return user;
      } else {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    }
  } catch (error) {
    console.warn('Error reading auth from localStorage:', error);
  }
  return null;
};

// Store user in localStorage
const storeUser = (user: User) => {
  const expiresAt = Date.now() + (24 * 60 * 60 * 1000); // 24 hours
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ user, expiresAt }));
};

// Remove user from localStorage
const removeStoredUser = () => {
  localStorage.removeItem(AUTH_STORAGE_KEY);
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isPending, setIsPending] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    const storedUser = getStoredUser();
    setUser(storedUser);

    // Set user context in Sentry if user exists
    if (storedUser) {
      setUserContext(storedUser);
      addBreadcrumb(`User session restored for ${storedUser.email}`, 'auth', 'info');
    }

    setIsPending(false);
  }, []);

  const login = async (email: string, _password: string): Promise<void> => {
    setIsPending(true);

    try {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Create mock user with provided email
      const authenticatedUser: User = {
        ...mockUser,
        email: email,
        name: email.split('@')[0] // Extract name from email
      };

      setUser(authenticatedUser);
      storeUser(authenticatedUser);

      // Set user context in Sentry for error tracking
      setUserContext(authenticatedUser);
      addBreadcrumb(`User ${authenticatedUser.email} logged in`, 'auth', 'info');
    } catch (error) {
      console.error('Mock login error:', error);
      throw new Error('Login failed');
    } finally {
      setIsPending(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsPending(true);

    try {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Clear user context in Sentry before logging out
      if (user) {
        addBreadcrumb(`User ${user.email} logged out`, 'auth', 'info');
      }
      clearUserContext();

      setUser(null);
      removeStoredUser();
    } catch (error) {
      console.error('Mock logout error:', error);
    } finally {
      setIsPending(false);
    }
  };

  const redirectToLogin = () => {
    // In a real app, this would redirect to OAuth provider
    // For mock, we'll just simulate the OAuth flow
    window.location.href = '/auth/callback?code=mock-auth-code';
  };

  const exchangeCodeForSessionToken = async (_code: string): Promise<void> => {
    setIsPending(true);

    try {
      // Simulate OAuth token exchange delay
      await new Promise(resolve => setTimeout(resolve, 800));

      // Set mock user after "successful" OAuth
      setUser(mockUser);
      storeUser(mockUser);

      // Set user context in Sentry for OAuth login
      setUserContext(mockUser);
      addBreadcrumb(`User ${mockUser.email} logged in via OAuth`, 'auth', 'info');
    } catch (error) {
      console.error('Mock OAuth error:', error);
      throw new Error('OAuth authentication failed');
    } finally {
      setIsPending(false);
    }
  };

  const value: AuthContextType = {
    user,
    isPending,
    login,
    logout,
    redirectToLogin,
    exchangeCodeForSessionToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
