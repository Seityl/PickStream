import { useLoaderData, Link, useNavigate } from 'react-router';
import { FaArrowLeft, FaClipboardList, FaExclamationTriangle, FaLock } from "react-icons/fa";
import MaterialRequestItem from '../components/MaterialRequestItem';
import { getMaterialRequests } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import { MatReqItem } from '../../types';

type LoaderData = {
  materialRequests: MatReqItem[] | null;
  error?: {
    type: string;
    message: string;
    status?: number;
  };
};

function MaterialRequestList() {
  const data = useLoaderData() as LoaderData;
  const navigate = useNavigate();
  
  // Extract data - handle both old format (direct array) and new format (object with error)
  const materialRequests = Array.isArray(data) ? data : data?.materialRequests;
  const error = Array.isArray(data) ? undefined : data?.error;

  // Handle permission error state
  if (error?.type === 'PermissionError') {
    return (
      <main>
        <header className='flex flex-row items-center px-4 sm:px-6 py-4 bg-white border-b border-gray-200 sticky top-0 z-10'>
          <Link 
            to={`/pick_stream/`}
            className="p-2 -ml-2 rounded-lg hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            aria-label="Go back to pick stream"
          >
            <FaArrowLeft size={16} className="text-gray-600"/>
          </Link>
          <h1 className='mx-auto text-lg font-semibold text-gray-900'>Material Requests</h1>
        </header>
        
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
                <button 
                  onClick={() => navigate('/pick_stream/')}
                  className='w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors'
                >
                  Return to Home
                </button>
                <p className='text-xs text-gray-500'>
                  Please contact IT to request access to material requests.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Handle general error state (network, server issues, etc.)
  if (error || materialRequests === null) {
    return (
      <main>
        <header className='flex flex-row items-center px-4 sm:px-6 py-4 bg-white border-b border-gray-200 sticky top-0 z-10'>
          <Link 
            to={`/pick_stream/`}
            className="p-2 -ml-2 rounded-lg hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-colors"
            aria-label="Go back to pick stream"
          >
            <FaArrowLeft size={16} className="text-gray-600"/>
          </Link>
          <h1 className='mx-auto text-lg font-semibold text-gray-900'>Material Requests</h1>
        </header>
        
        <div className='flex items-center justify-center min-h-[60vh] px-4'>
          <div className='text-center'>
            <div className='bg-white p-8 rounded-xl shadow-sm border border-red-200 max-w-md'>
              <div className='bg-red-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4'>
                <FaExclamationTriangle className='text-red-500 text-xl' />
              </div>
              <h2 className='text-lg font-semibold text-gray-900 mb-2'>
                {error?.type === 'NetworkError' ? 'Connection Error' : 'Unable to Load Material Requests'}
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
                <button 
                  onClick={() => navigate('/pick_stream/')}
                  className='w-full bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors'
                >
                  Return to Home
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

  return (
    <main>
      {/* Header */}
      <header className='bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm'>
        <div className='px-4 sm:px-6 py-4'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-4'>
              <Link 
                to={`/pick_stream/`}
                className="p-2 -ml-2 rounded-lg hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all duration-200 group"
                aria-label="Go back to pick stream"
              >
                <FaArrowLeft size={16} className="text-gray-600 group-hover:text-gray-900 group-hover:translate-x-[-1px] transition-all duration-200"/>
              </Link>
              
              <div>
                <h1 className='text-xl font-semibold text-gray-900'>Material Requests</h1>
                <p className='text-sm text-gray-500 mt-0.5'>
                  {materialRequests.length === 0 
                    ? 'No active requests' 
                    : `${materialRequests.length} ${materialRequests.length === 1 ? 'request' : 'requests'} assigned to you`
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Content Area */}
      <div className='pb-8'>
        {materialRequests.length > 0 ? (
          <>
            {/* Request List */}
            <div className='px-4 sm:px-6 pt-6'>
              <div className='space-y-4'>
                {materialRequests.map((materialRequest: MatReqItem, index: number) => (
                  <div 
                    key={materialRequest.name || index} 
                    className='bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-gray-300 transition-all duration-200 overflow-hidden'
                  >
                    <MaterialRequestItem {...materialRequest} />
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className='flex items-center justify-center min-h-[60vh] px-4'>
            <div className='text-center max-w-md'>
              <div className='bg-white p-8 rounded-2xl shadow-sm border border-gray-200'>
                <div className='bg-gray-50 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6'>
                  <FaClipboardList className='text-gray-400 text-3xl' />
                </div>
                
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                  All Caught Up!
                </h2>
                
                <p className='text-gray-600 mb-6 leading-relaxed'>
                  You don't have any pending material requests right now. New requests will appear here as they're assigned to you.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default MaterialRequestList;

export async function materialRequestLoader() {
  try {
    const user = await getCurrentUser();
    console.log('Material request loader - User:', user);
    
    if (!user) {
      throw new Error('User not authenticated');
    }
    
    const response = await getMaterialRequests(user);
    console.log('Material requests response:', response);
    
    // Check if response contains an error structure (like 403 Permission Error)
    if (response?.message?.error) {
      const errorType = response.message.error.error_type;
      const errorMessage = response.message.error.error_message;
      
      console.error('API returned error:', response.message.error);
      
      return {
        materialRequests: null,
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
        materialRequests: null,
        error: {
          type: 'ServerError',
          message: 'Failed to load material requests. Please try again.',
          status: response.message.status
        }
      };
    }
    
    // Helper function to normalize a single material request
    const normalizeMaterialRequest = (mr: any): MatReqItem => ({
      name: mr.name || '',
      target_warehouse: mr.target_warehouse || '',
      source_warehouse: mr.source_warehouse || '',
      status: mr.status || 'Open',
      // Ensure item_group_availability is an object, not an array
      item_group_availability: 
        typeof mr.item_group_availability === 'object' && !Array.isArray(mr.item_group_availability)
          ? mr.item_group_availability 
          : {}
    });
    
    // Handle case where response has the data nested in message.data
    if (response?.message?.data && Array.isArray(response.message.data)) {
      const materialRequests = response.message.data;
      const normalizedRequests = materialRequests.map(normalizeMaterialRequest);
      
      console.log('Normalized material requests:', normalizedRequests);
      return {
        materialRequests: normalizedRequests
      };
    }
    
    // Handle direct array response (backwards compatibility)
    if (Array.isArray(response)) {
      const normalizedRequests = response.map(normalizeMaterialRequest);
      return {
        materialRequests: normalizedRequests
      };
    }
    
    // If response exists but isn't an array or expected structure, return empty array
    return {
      materialRequests: response ? [] : []
    };
  } catch (error) {
    console.error('Failed to load material requests:', error);
    
    // Determine error type
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network');
    
    // Return error state to trigger error UI in component
    return {
      materialRequests: null,
      error: {
        type: isNetworkError ? 'NetworkError' : 'LoadError',
        message: isNetworkError 
          ? 'Unable to connect to the server. Please check your internet connection.'
          : 'Failed to load material requests. Please try again.'
      }
    };
  }
}