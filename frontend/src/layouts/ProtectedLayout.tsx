import { useEffect } from 'react';
import { useNavigate, useLocation, Outlet, useNavigation } from 'react-router';
import { CgSpinnerTwo } from "react-icons/cg";
import { useFrappeAuth } from 'frappe-react-sdk';
// import { useAuth } from '../context/AuthContext';

const ProtectedLayout = () => {
  const {currentUser, isLoading} = useFrappeAuth();
  // const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const location = useLocation();


  useEffect(() => {
    if (/*!isAuthenticated*/ !isLoading && !currentUser) {
      console.log("currentUser is not set")
      navigate('/pick_stream/login', { replace: true, state: { from: location } });
    }
  }, [/*isAuthenticated*/ currentUser, isLoading, navigate, location]);
  
  return /*isAuthenticated*/ !isLoading ? <div className='relative min-h-screen'>{navigation.state == "loading" ?  <CgSpinnerTwo className='spin' /> : <Outlet /> }</div> : null;
};

export default ProtectedLayout;
