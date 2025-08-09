import { useEffect, useState } from 'react';
import { useNavigate, useLocation, Outlet, useNavigation } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { useAuth } from '../context/AuthContext';
import { validateSession } from '../../utils/auth';

const ProtectedLayout = () => {
  const { isLoading, isAuthenticated, signOut } = useAuth();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const location = useLocation();
  const [isValidatingRoute, setIsValidatingRoute] = useState(false);

  // Original route protection - commented for rollback
  // useEffect(() => {
  //   if (!isLoading && !isAuthenticated) {
  //     navigate('/pick_stream/login', { replace: true });
  //   }
  // }, [isAuthenticated, isLoading, navigate]);

  // Enhanced route protection with session validation
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/pick_stream/login', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  // Additional session validation on route changes
  useEffect(() => {
    const validateRouteAccess = async () => {
      if (isAuthenticated && !isLoading) {
        setIsValidatingRoute(true);
        try {
          const isSessionValid = await validateSession();
          if (!isSessionValid) {
            console.warn('Session invalid on route change, signing out');
            await signOut();
          }
        } catch (error) {
          console.error('Route validation error:', error);
          await signOut();
        } finally {
          setIsValidatingRoute(false);
        }
      }
    };

    validateRouteAccess();
  }, [location.pathname, isAuthenticated, isLoading, signOut]);

  // Show loading for initial auth or route validation
  if (isLoading || isValidatingRoute) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CgSpinnerTwo className="animate-spin text-4xl mx-auto mb-2" />
          <p className="text-sm text-gray-600">
            {isLoading ? 'Loading...' : 'Validating session...'}
          </p>
        </div>
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
