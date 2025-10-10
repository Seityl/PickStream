import { NavLink, Outlet, useNavigation } from 'react-router';
import { FaHome, FaTools } from "react-icons/fa";
import { BiSolidBellRing } from "react-icons/bi";
import { IoPersonSharp } from "react-icons/io5";
import PageLoader from '../components/PageLoader';

const TabLayout = () => {
  const navigation = useNavigation();
  const navItems = [
    { 
      path: "/pick_stream", 
      icon: FaHome, 
      label: "Home",
      end: true 
    },
    { 
      path: "/pick_stream/tools", 
      icon: FaTools, 
      label: "Tools",
      end: false 
    },
    { 
      path: "/pick_stream/notifications", 
      icon: BiSolidBellRing, 
      label: "Alerts",
      end: false 
    },
    { 
      path: "/pick_stream/profile", 
      icon: IoPersonSharp, 
      label: "Profile",
      end: false 
    }
  ];

  // Show global loader for route transitions
  const isNavigating = navigation.state === "loading";

  return (
    <div className='main-container relative'>
      {isNavigating ? <PageLoader variant="entertaining" /> : <Outlet />}
      <div className="fixed bottom-0 left-1/2 -translate-x-1/2 z-50 w-full max-w-[428px] bg-white border-t border-gray-200 shadow-lg">
        <div className="flex flex-row justify-between items-center h-16 px-4">
          {navItems.map(({ path, icon: Icon, label, end }) => (
            <NavLink 
              key={path}
              to={path} 
              end={end}
              className={({ isActive }) => 
                `flex flex-col items-center justify-center flex-1 py-2 px-1 transition-all duration-200 ${
                  isActive 
                    ? 'text-blue-600' 
                    : 'text-gray-500 hover:text-gray-700 active:scale-95'
                }`
              }
            >
              <Icon className='text-2xl mb-1' />
              <span className='text-xs font-medium'>{label}</span>
            </NavLink>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TabLayout;