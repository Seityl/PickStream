import {useLoaderData} from 'react-router';
import { getNotifications } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

function Notifications() {
  const notifications = useLoaderData() as any[]; // Using any for now as we don't have the type

  // Placeholder data for UI development
  const placeholderNotifications = [
    {
      id: 1,
      title: 'New Item Received',
      message: 'Item "ITM-0001" has been successfully received.',
      timestamp: '2 hours ago',
      read: false,
    },
    {
      id: 2,
      title: 'Crate in Transit',
      message: 'Crate "CRT-0012" is now in transit to King George branch.',
      timestamp: '1 day ago',
      read: true,
    },
    {
      id: 3,
      title: 'Verification Required',
      message: 'Item "ITM-0025" requires verification.',
      timestamp: '3 days ago',
      read: true,
    },
  ];

  const displayNotifications = notifications?.length ? notifications : placeholderNotifications;

  return (
    <main className="min-h-screen bg-gray-50 p-4">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Notifications</h1>
      <div className="bg-white rounded-lg shadow-sm">
        <ul className="divide-y divide-gray-200">
          {displayNotifications.map((notification) => (
            <li key={notification.id} className={`p-4 ${!notification.read ? 'bg-blue-50' : ''}`}>
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  {/* Icon can be conditional based on notification type */}
                  <svg className="h-6 w-6 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-4 flex-grow">
                  <p className="text-sm font-medium text-gray-900">{notification.title}</p>
                  <p className="text-sm text-gray-500">{notification.message}</p>
                </div>
                <div className="ml-4 flex-shrink-0">
                  <p className="text-xs text-gray-400">{notification.timestamp}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}

export default Notifications;


export async function notificationsLoader() {
  const user = await getCurrentUser();
  return await getNotifications(user!);
}
