// import axiosClient from '../../utils/client';
import frappeClient from '../../utils/client';
import {
  useContext,
  createContext,
  type PropsWithChildren,
  useState,
} from 'react';
import { useStorageState } from '../hooks/useStorageState';

const AuthContext = createContext<{
  signIn: (email: string, password: string) => Promise<any>;
  signOut: () => Promise<any>;
  user?: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}>({
  signIn: async () => null,
  signOut: async () => null,
  user: null,
  isLoading: false,
  isAuthenticated: false,
});

// This hook can be used to access the user info.
export function useAuth() {
  const value = useContext(AuthContext);
  return value;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useStorageState('user');
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(
    !!localStorage.getItem('user')
  );
  const auth = frappeClient.auth();

  return (
    <AuthContext.Provider
      value={{
        signIn: async (email: string, password: string) => {
          try {
            setIsLoading(true);

            const response = await auth.loginWithUsernamePassword({
              username: email,
              password: password,
            });

            if (response.message === 'Logged In') {
              const loggedInUser = await auth.getLoggedInUser();
              setUser(loggedInUser);
              setIsAuthenticated(true);
            }

            console.log(user);
            setIsLoading(false);
          } catch (e) {
            setIsLoading(false);
            setIsAuthenticated(false);
            return { error: true, msg: (e as any).response.data.message };
          }
        },
        signOut: async () => {
          setIsLoading(true);

          await auth.logout();
          setUser(null);
          setIsAuthenticated(false);

          setIsLoading(false);
        },
        user,
        isLoading,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
