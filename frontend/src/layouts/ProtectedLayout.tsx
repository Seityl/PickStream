import { useEffect } from 'react';
import { useNavigate, useLocation, Outlet, useNavigation } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { useAuth } from '../context/AuthContext';

const ProtectedLayout = () => {
  const { isLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/pick_stream/login', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <CgSpinnerTwo className="animate-spin text-4xl" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      {navigation.state === "loading" && (
        <div className="fixed top-4 right-4 z-50">
          <CgSpinnerTwo className="animate-spin text-2xl" />
        </div>
      )}
      <Outlet />
    </div>
  );
};

export default ProtectedLayout;
