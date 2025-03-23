import { useEffect } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router';
import { useAuth } from '../context/AuthContext';

const ProtectedLayout = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, navigate, location]);

  return isAuthenticated ? <Outlet /> : null;
};

export default ProtectedLayout;
