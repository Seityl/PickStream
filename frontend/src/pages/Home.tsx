import {Link} from 'react-router';
import { FaFileAlt } from "react-icons/fa";
import { PiBoxArrowDown } from "react-icons/pi";
import { FaTruck } from "react-icons/fa6";
import { MdDomainVerification } from "react-icons/md";

export default function Home() {
  const navItems = [
    { path: '/pick_stream/material-requests', label: 'Picking', icon: FaFileAlt },
    { path: '/pick_stream/transit', label: 'Transit', icon: FaTruck },
    { path: '/pick_stream/verification', label: 'Verification', icon: MdDomainVerification },
    { path: '/pick_stream/receiving', label: 'Receiving', icon: PiBoxArrowDown }
    // { path: '/logs', label: 'Logs', icon: ClipboardList },
    // { path: '/notifications', label: 'Alerts', icon: Bell },
    // { path: '/profile', label: 'Profile', icon: User },
    // { path: '/settings', label: 'Settings', icon: Settings },
    // { path: '/materials', label: 'Materials', icon: Package },
  ];
  return (
  <main>
     <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4">
      {navItems.map(({ path, label, icon: Icon }) => (
        <Link
          key={path}
          to={path}
          className="flex flex-col items-center justify-center p-4 bg-gray-100 rounded-lg shadow-md transition-transform active:scale-95"
        >
          <Icon size={32} className="text-blue-500" />
          <span className="mt-2 text-sm font-medium">{label}</span>
        </Link>
      ))}
    </div>
  </main>);
}
