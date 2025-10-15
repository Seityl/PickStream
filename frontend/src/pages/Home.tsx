import { useLoaderData, useNavigate } from 'react-router';
import { FaFileAlt, FaTruck, FaExclamationTriangle, FaLock } from "react-icons/fa";
import { PiBoxArrowDown } from "react-icons/pi";
import { MdDomainVerification } from "react-icons/md";
import { getCurrentUser } from '../../utils/auth';
import { getUserWorkflowAccess } from '../../utils/api';

interface WorkflowAccess {
  picking: boolean;
  transit: boolean;
  verification: boolean;
  receiving: boolean;
}

type LoaderData = {
  workflowAccess: WorkflowAccess | null;
  error?: {
    type: string;
    message: string;
    status?: number;
  };
};

export default function Home() {
  const data = useLoaderData() as LoaderData;
  const navigate = useNavigate();
  
  // Extract data - handle both old format (direct object) and new format (object with error)
  const workflowAccess = data && 'workflowAccess' in data ? data.workflowAccess : data as WorkflowAccess;
  const error = data && 'error' in data ? data.error : undefined;

  const allNavItems = [
    { 
      path: '/pick_stream/material-requests', 
      label: 'Picking', 
      icon: FaFileAlt,
      description: 'Pick items from material requests',
      accessKey: 'picking'
    },
    { 
      path: '/pick_stream/transit', 
      label: 'Transit', 
      icon: FaTruck,
      description: 'Add items to transit',
      accessKey: 'transit'
    },
    { 
      path: '/pick_stream/verification', 
      label: 'Verification', 
      icon: MdDomainVerification,
      description: 'Verify picked items',
      accessKey: 'verification'
    },
    { 
      path: '/pick_stream/receiving', 
      label: 'Receiving', 
      icon: PiBoxArrowDown,
      description: 'Receive incoming items',
      accessKey: 'receiving'
    }
  ];

  // Handle permission error state
  if (error?.type === 'PermissionError') {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className='flex items-center justify-center min-h-[60vh] px-4'>
          <div className='text-center'>
            <div className='bg-white p-8 rounded-xl shadow-sm border border-amber-200 max-w-md'>
              <div className='bg-amber-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4'>
                <FaLock className='text-amber-600 text-xl' />
              </div>
              <h2 className='text-lg font-semibold text-gray-900 mb-2'>Access Denied</h2>
              <p className='text-gray-600 text-sm mb-4 leading-relaxed'>
                {error.message}
              </p>
              <div className='space-y-3'>
                <p className='text-xs text-gray-500'>
                  Please contact your administrator to request workflow access.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Handle general error state
  if (error || workflowAccess === null) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className='flex items-center justify-center min-h-[60vh] px-4'>
          <div className='text-center'>
            <div className='bg-white p-8 rounded-xl shadow-sm border border-red-200 max-w-md'>
              <div className='bg-red-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4'>
                <FaExclamationTriangle className='text-red-500 text-xl' />
              </div>
              <h2 className='text-lg font-semibold text-gray-900 mb-2'>
                {error?.type === 'NetworkError' ? 'Connection Error' : 'Unable to Load Workflow Access'}
              </h2>
              <p className='text-gray-600 text-sm mb-4 leading-relaxed'>
                {error?.message || "We're having trouble connecting to the server. This could be a temporary network issue."}
              </p>
              <div className='space-y-3'>
                <button 
                  onClick={() => window.location.reload()} 
                  className='w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors'
                >
                  Try Again
                </button>
                <p className='text-xs text-gray-500'>
                  If this problem continues, please contact IT.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Filter nav items based on user access
  const accessibleNavItems = allNavItems.filter(item => 
    workflowAccess[item.accessKey as keyof WorkflowAccess]
  );

  return (
    <main className="p-4 max-w-4xl mx-auto">
      {/* Header Section */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome Back</h1>
        <p className="text-gray-600">
          {accessibleNavItems.length === 0 
            ? 'No workflows available' 
            : 'Select a workflow to continue'
          }
        </p>
      </div>

      {/* Navigation Cards */}
      {accessibleNavItems.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {accessibleNavItems.map(({ path, label, icon: Icon, description }) => (
            <div
              key={path}
              onClick={() => navigate(path)}
              className="group cursor-pointer block p-6 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:border-blue-200 transition-all duration-200 active:scale-[0.98]"
            >
              <div className="flex items-start space-x-4">
                <div className="p-3 bg-blue-50 rounded-xl group-hover:bg-blue-100 transition-colors">
                  <Icon size={28} className="text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-blue-700 transition-colors">
                    {label}
                  </h3>
                  <p className="text-gray-500 mb-4 leading-relaxed">{description}</p>
                  
                  <div className="flex items-center text-blue-600 text-sm font-medium group-hover:text-blue-700">
                    Go to {label}
                    <svg className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* No Access State */
        <div className='flex items-center justify-center min-h-[40vh] px-4'>
          <div className='text-center max-w-md'>
            <div className='bg-white p-8 rounded-2xl shadow-sm border border-gray-200'>
              <div className='bg-gray-50 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6'>
                <FaExclamationTriangle className='text-gray-400 text-3xl' />
              </div>
              
              <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                No Workflows Available
              </h2>
              
              <p className='text-gray-600 mb-6 leading-relaxed'>
                You don't currently have access to any workflows. Please contact your administrator to request access.
              </p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export async function homeLoader() {
  try {
    const user = await getCurrentUser();
    console.log('home loader - user:', user);
    
    if (!user) {
      throw new Error('User not authenticated');
    }
    
    const response = await getUserWorkflowAccess(user);
    console.log('workflow access response:', response);
    
    // Check if response contains an error structure (like 403 Permission Error)
    if (response?.message?.error) {
      const errorType = response.message.error.error_type;
      const errorMessage = response.message.error.error_message;
      
      console.error('API returned error:', response.message.error);
      
      return {
        workflowAccess: null,
        error: {
          type: errorType,
          message: errorMessage,
          status: response.message.status
        }
      };
    }
    
    // Check for HTTP error status
    if (response?.message?.status && response.message.status >= 400) {
      console.error('API returned error status:', response.message.status);
      return {
        workflowAccess: null,
        error: {
          type: 'ServerError',
          message: 'Failed to load workflow access. Please try again.',
          status: response.message.status
        }
      };
    }
    
    // Handle case where response has the data nested in message.data
    if (response?.message?.data && typeof response.message.data === 'object') {
      return {
        workflowAccess: response.message.data
      };
    }
    
    // Handle direct response (backwards compatibility)
    if (response && typeof response === 'object' && !response.message) {
      return {
        workflowAccess: response
      };
    }
    
    // Return null to trigger error state if response is unexpected
    return {
      workflowAccess: null,
      error: {
        type: 'UnexpectedResponse',
        message: 'Received unexpected response from server. Please try again.'
      }
    };
  } catch (error) {
    console.error('Failed to load workflow access:', error);
    
    // Determine error type
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network');
    
    // Return error state to trigger error UI in component
    return {
      workflowAccess: null,
      error: {
        type: isNetworkError ? 'NetworkError' : 'LoadError',
        message: isNetworkError 
          ? 'Unable to connect to the server. Please check your internet connection.'
          : 'Failed to load workflow access. Please try again.'
      }
    };
  }
}