import { useEffect, useState } from 'react';
import { useNavigate, useLocation, Outlet, useNavigation } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { FaShieldAlt, FaRoute } from "react-icons/fa";
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
      {/* Enhanced navigation loader - centered with blurred backdrop */}
      {navigation.state === "loading" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
          <div className="bg-white/95 backdrop-blur-md rounded-lg shadow-xl border border-gray-200/50 p-4 flex items-center space-x-3 mx-4">
            <CgSpinnerTwo className="animate-spin text-xl text-blue-600" />
            <div>
              <p className="text-sm font-medium text-gray-900">Loading</p>
              <p className="text-xs text-gray-500">Please wait...</p>
            </div>
          </div>
        </div>
      )}
      
      {/* Navigation progress bar - centered with backdrop */}
      {navigation.state === "loading" && (
        <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-8 z-40 w-64">
          <div className="h-1.5 bg-white/30 backdrop-blur-sm rounded-full border border-white/20">
            <div 
              className="h-1.5 bg-blue-500/80 rounded-full shadow-sm" 
              style={{
                width: '70%',
                animation: 'navProgress 1s ease-in-out infinite'
              }}
            ></div>
          </div>
        </div>
      )}
      
      <Outlet />
      
      {/* Global CSS animations */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes loadingProgress {
            0% { width: 20%; }
            50% { width: 80%; }
            100% { width: 20%; }
          }
          
          @keyframes navProgress {
            0% { width: 10%; }
            50% { width: 80%; }
            100% { width: 10%; }
          }
        `
      }} />
    </div>
  );
};

export default ProtectedLayout;