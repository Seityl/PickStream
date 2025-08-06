import {JSX} from 'react';
import { Navigate } from 'react-router';
import { useAuth } from '../context/AuthContext';

interface RedirectIfLoggedInProps {
  children: JSX.Element;
}

export const RedirectIfLoggedIn = ({ children }: RedirectIfLoggedInProps) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/pick_stream" replace /> : children;
};
