// import { useEffect } from 'react';
import { NavLink, Outlet } from 'react-router';
import { FaHome } from "react-icons/fa";
import { FaTools } from "react-icons/fa";
import { BiSolidBellRing } from "react-icons/bi";
import { IoPersonSharp } from "react-icons/io5";
const TabLayout = () => {

  return (
  <div className='main-container relative'>
    <Outlet />
    <div className="fixed bottom-0 left-0 z-50 w-full h-16 bg-white border-t border-gray-200 dark:bg-gray-700 dark:border-gray-600">
    <div className="flex flex-row justify-between items-center h-full max-w-lg mx-auto font-medium px-8">
        <NavLink className='nav-link' to="/pick_stream" end>
          <FaHome className='text-3xl' />
        </NavLink>

        <NavLink className='nav-link' to="/pick_stream/tools">
          <FaTools className='text-3xl'/>
        </NavLink>

        <NavLink className='nav-link' to="/pick_stream/notifications">
          <BiSolidBellRing className='text-3xl'/>
        </NavLink>

        <NavLink className='nav-link' to="/pick_stream/profile">
          <IoPersonSharp className='text-3xl'/>
        </NavLink>
    </div>
</div>

  </div>
  );
};

export default TabLayout;
