import { useEffect, useState } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { FaShieldAlt, FaRoute } from "react-icons/fa";
import { useAuth } from '../context/AuthContext';
import { validateSession } from '../../utils/auth';

const ProtectedLayout = () => {
  const { isLoading, isAuthenticated, signOut } = useAuth();
  const navigate = useNavigate();
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

  // Enhanced loading screen for initial auth or route validation
  if (isLoading || isValidatingRoute) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 backdrop-blur-sm">
        <div className="text-center p-8 bg-white/90 backdrop-blur-md rounded-lg shadow-lg border border-gray-200/50 max-w-sm mx-4">
          <div className="mb-4">
            {/* Icon based on loading type */}
            <div className="relative inline-flex items-center justify-center">
              <div className={`p-3 rounded-full mb-2 ${
                isLoading 
                  ? 'bg-blue-50 border border-blue-100' 
                  : 'bg-green-50 border border-green-100'
              }`}>
                {isLoading ? (
                  <FaShieldAlt className="text-blue-600" size={24} />
                ) : (
                  <FaRoute className="text-green-600" size={24} />
                )}
              </div>
              
              {/* Spinning loader overlay */}
              <div className="absolute inset-0 flex items-center justify-center">
                <CgSpinnerTwo className="animate-spin text-3xl text-gray-400" />
              </div>
            </div>
          </div>
          
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {isLoading ? 'Authenticating' : 'Validating Session'}
          </h3>
          
          <p className="text-sm text-gray-600 mb-4">
            {isLoading 
              ? 'Setting up your secure session...' 
              : 'Verifying your access permissions...'
            }
          </p>
          
          {/* Progress indicator */}
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div 
              className={`h-1.5 rounded-full ${
                isLoading ? 'bg-blue-500' : 'bg-green-500'
              }`} 
              style={{
                width: '60%',
                animation: 'loadingProgress 2s ease-in-out infinite'
              }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      {/* Navigation loading is now handled by individual page components with PageLoader */}
      {/* This allows each page to show its own customized loader experience */}
      <Outlet />

      {/* Global CSS animations for auth loading */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes loadingProgress {
            0% { width: 20%; }
            50% { width: 80%; }
            100% { width: 20%; }
          }
        `
      }} />
    </div>
  );
};

export default ProtectedLayout;