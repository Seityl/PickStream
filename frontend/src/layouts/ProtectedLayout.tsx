import { useEffect } from 'react';
import { useNavigate, useLocation, Outlet, useNavigation } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { useAuth } from '../context/AuthContext';

const ProtectedLayout = () => {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/pick_stream/login', { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, navigate, location]);
  
  return isAuthenticated ? <div className='relative min-h-screen'>{navigation.state == "loading" ?  <CgSpinnerTwo className='spin' /> : <Outlet /> }</div> : null;
};

export default ProtectedLayout;
