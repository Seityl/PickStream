import { useEffect } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router';
import { useAuth } from '../context/AuthContext';

const ProtectedRoute = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/pick_stream/login', { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, navigate, location]);

  return isAuthenticated ? <Outlet /> : null;
};

export default ProtectedRoute;
