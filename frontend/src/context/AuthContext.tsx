import React, {
  useContext,
  useEffect,
  createContext,
  type PropsWithChildren,
  useState,
} from 'react';
import { frappeAuth } from '../../utils/client';
import { getCurrentUser, clearUserSession } from '../../utils/auth';
import { useStorageState } from '../hooks/useStorageState';

interface AuthContextType {
  signIn: (email: string, password: string) => Promise<{ error?: boolean; msg?: string }>;
  signOut: () => Promise<void>;
  user: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  signIn: async () => ({ error: true, msg: 'Not implemented' }),
  signOut: async () => {},
  user: null,
  isLoading: false,
  isAuthenticated: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useStorageState('user');
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    async function initAuth() {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setIsAuthenticated(!!currentUser);
      setIsLoading(false);
    }
    initAuth();
  }, [setUser]);

  useEffect(() => {
    setIsAuthenticated(!!user);
  }, [user]);

  const signIn = async (email: string, password: string) => {
    try {
      setIsLoading(true);

      const response = await frappeAuth.loginWithUsernamePassword({
        username: email,
        password: password,
      });

      if (response.message === 'Logged In') {
        const loggedInUser = await frappeAuth.getLoggedInUser();
        setUser(loggedInUser);
        setIsAuthenticated(true);
        return { error: false };
      }

      return { error: true, msg: 'Login failed' };
    } catch (error: any) {
      setIsAuthenticated(false);
      return {
        error: true,
        msg: error?.response?.data?.message || 'Login failed',
      };
    } finally {
      setIsLoading(false);
    }
  };

  const signOut = async () => {
    try {
      await frappeAuth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearUserSession();
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        signIn,
        signOut,
        user,
        isLoading,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
