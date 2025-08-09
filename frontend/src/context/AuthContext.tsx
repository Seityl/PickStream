import React, {
  useContext,
  useEffect,
  createContext,
  type PropsWithChildren,
  useState,
} from 'react';
import { frappeAuth } from '../../utils/client';
import { getCurrentUser, clearUserSession, startSessionMonitoring, stopSessionMonitoring, validateSession } from '../../utils/auth';
import { useStorageState } from '../hooks/useStorageState';

interface AuthContextType {
  signIn: (email: string, password: string) => Promise<{ error?: boolean; msg?: string }>;
  signOut: () => Promise<void>;
  user: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null || context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useStorageState('user');
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Original initAuth - commented for rollback
  // useEffect(() => {
  //   async function initAuth() {
  //     const currentUser = await getCurrentUser();
  //     if (currentUser) {
  //       setUser(currentUser);
  //       setIsAuthenticated(true);
  //     }
  //     setIsLoading(false);
  //   }
  //   initAuth();
  // }, [setUser]);

  // Enhanced authentication initialization with session validation
  useEffect(() => {
    async function initAuth() {
      try {
        // First check if we have a stored user
        const storedUser = localStorage.getItem('user');
        if (storedUser && storedUser !== 'null' && storedUser !== 'undefined') {
          // Validate the session before trusting the stored user
          const isSessionValid = await validateSession();
          if (isSessionValid) {
            const currentUser = await getCurrentUser();
            if (currentUser) {
              setUser(currentUser);
              setIsAuthenticated(true);
              // Start session monitoring for authenticated users
              startSessionMonitoring(() => {
                console.log('Session expired, signing out user');
                // Use direct cleanup instead of signOut to avoid dependency issues
                stopSessionMonitoring();
                clearUserSession();
                setUser(null);
                setIsAuthenticated(false);
              }, 300000); // Check every 5 minutes
              setIsLoading(false);
              return;
            }
          }
        }
        
        // If no valid session, clear everything
        clearUserSession();
        setUser(null);
        setIsAuthenticated(false);
      } catch (error) {
        console.error('Auth initialization error:', error);
        clearUserSession();
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, [setUser]);

  useEffect(() => {
    setIsAuthenticated(!!user);
  }, [user]);

  // Cleanup session monitoring on unmount
  useEffect(() => {
    return () => {
      stopSessionMonitoring();
    };
  }, []);

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
        
        // Start session monitoring for newly authenticated users
        startSessionMonitoring(() => {
          console.log('Session expired during active session, signing out user');
          // Use direct cleanup instead of signOut to avoid dependency issues
          stopSessionMonitoring();
          clearUserSession();
          setUser(null);
          setIsAuthenticated(false);
        }, 300000); // Check every 5 minutes
        
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

  // Original signOut - commented for rollback
  // const signOut = async () => {
  //   try {
  //     await frappeAuth.logout();
  //   } catch (error) {
  //     console.error('Logout error:', error);
  //   } finally {
  //     clearUserSession();
  //     setUser(null);
  //     setIsAuthenticated(false);
  //   }
  // };

  // Enhanced signOut with session monitoring cleanup
  const signOut = async () => {
    try {
      // Stop session monitoring
      stopSessionMonitoring();
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
