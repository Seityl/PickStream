import { useLoaderData } from 'react-router';
import { getNotifications } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

function Notifications() {
  const notificationsData = useLoaderData() as any;
  
  // Extract notifications from the API response structure
  const notifications = notificationsData || [];

  // Function to get notification icon
  const getNotificationIcon = () => {
    return (
      <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
        <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM9 7H4l5-5v5zm0 0h6v6H9V7z" />
        </svg>
      </div>
    );
  };

  // Function to format timestamp
  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return '';
    
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
      
      if (diffInSeconds < 60) return 'Just now';
      if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
      if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
      if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
      
      return date.toLocaleDateString();
    } catch (error) {
      return timestamp; // Return original if parsing fails
    }
  };

  return (
    <main className="bg-gray-50">
      {/* Header Section */}
      <div className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
              <p className="text-sm text-gray-600 mt-1">
                {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        {notifications.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM9 7H4l5-5v5zm0 0h6v6H9V7z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No notifications
            </h3>
            <p className="text-gray-500">
              You're all caught up! No notifications to display.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <ul className="divide-y divide-gray-100">
              {notifications.map((notification: any, index: number) => (
                <li 
                  key={notification.id || notification.name || index}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start space-x-4">
                    {/* Notification Icon */}
                    <div className="flex-shrink-0 mt-1">
                      {getNotificationIcon()}
                    </div>
                    
                    {/* Notification Content */}
                    <div className="flex-grow min-w-0">
                      <div className="flex items-start justify-between">
                        <div className="flex-grow">
                          <h3 className="text-sm font-medium text-gray-900">
                            {notification.title || notification.subject || 'Notification'}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                            {notification.message || notification.content || 'No message content'}
                          </p>
                          
                          {/* Additional metadata if available */}
                          {(notification.document_type || notification.document_name) && (
                            <div className="flex items-center mt-2 space-x-2">
                              {notification.document_type && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                  {notification.document_type}
                                </span>
                              )}
                              {notification.document_name && (
                                <span className="text-xs text-gray-500 truncate">
                                  {notification.document_name}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        
                        {/* Timestamp */}
                        <div className="flex-shrink-0 ml-4 text-right">
                          <p className="text-xs text-gray-500">
                            {formatTimestamp(notification.creation || notification.timestamp)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}

export default Notifications;

export async function notificationsLoader() {
  try {
    const user = await getCurrentUser();
    if (!user) {
      throw new Error('No authenticated user found');
    }
    return await getNotifications(user);
  } catch (error) {
    console.error('Notifications loader error:', error);
    // Return empty notifications data to prevent app crash
    return { 
      message: { 
        status: 500, 
        data: [] 
      } 
    };
  }
}