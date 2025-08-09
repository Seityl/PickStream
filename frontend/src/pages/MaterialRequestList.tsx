import { useLoaderData, Link, useNavigation } from 'react-router';
import { FaArrowLeft, FaClipboardList, FaSpinner, FaExclamationTriangle } from "react-icons/fa";
import MaterialRequestItem from '../components/MaterialRequestItem';
import { getMaterialRequests } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import { MatReqItem } from '../../types';

function MaterialRequestList() {
  const materialRequests = useLoaderData() as MatReqItem[] | null;
  const navigation = useNavigation();
  const isLoading = navigation.state === "loading";

  // Handle loading state
  if (isLoading) {
    return (
      <main className='min-h-screen bg-gray-50'>
        <header className='flex flex-row items-center px-4 sm:px-6 py-4 bg-white border-b border-gray-200 sticky top-0 z-10'>
          <div className="flex items-center w-full">
            <div className="w-8 h-8 bg-gray-200 rounded-lg animate-pulse"></div>
            <div className="mx-auto h-6 w-32 bg-gray-200 rounded animate-pulse"></div>
          </div>
        </header>
        
        <div className='flex items-center justify-center min-h-[60vh]'>
          <div className='text-center'>
            <div className='bg-white p-6 rounded-xl shadow-sm border border-gray-200'>
              <FaSpinner className='animate-spin text-2xl text-blue-500 mx-auto mb-3' />
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Handle error state
  if (!materialRequests) {
    return (
      <main className='min-h-screen bg-gray-50'>
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
              <h2 className='text-lg font-semibold text-gray-900 mb-2'>Unable to Load Material Requests</h2>
              <p className='text-gray-600 text-sm mb-4 leading-relaxed'>
                We're having trouble connecting to the server. This could be a temporary network issue.
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

  return (
    <main className='min-h-screen bg-gray-50'>
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
                    key={index} 
                    className='bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-gray-300 transition-all duration-200 overflow-hidden'
                  >
                    <MaterialRequestItem {...materialRequest} />
                  </div>
                ))}
              </div>

              {/* Pagination placeholder */}
              {materialRequests.length > 10 && (
                <div className='mt-8 flex justify-center'>
                  <div className='bg-white px-6 py-3 rounded-lg border border-gray-200 shadow-sm'>
                    <p className='text-sm text-gray-600'>
                      Showing {Math.min(materialRequests.length, 10)} of {materialRequests.length} requests
                    </p>
                  </div>
                </div>
              )}
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

                <div className='bg-blue-50 p-4 rounded-lg border border-blue-200'>
                  <p className='text-sm text-blue-700 font-medium'>
                    💡 Tip: Check back regularly or enable notifications to stay on top of new requests
                  </p>
                </div>
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
    console.log('material request loader - ', user);
    
    if (!user) {
      throw new Error('User not authenticated');
    }
    
    const response = await getMaterialRequests(user);
    console.log('material requests response -', response);
    
    // Check if response contains an error structure
    if (response && response.message && response.message.status >= 400) {
      console.error('API returned error:', response.message.error);
      return null; // Trigger error state
    }
    
    // Handle case where response has the data nested in message.data
    if (response && response.message && Array.isArray(response.message.data)) {
      return response.message.data;
    }
    
    // Handle direct array response
    if (Array.isArray(response)) {
      return response;
    }
    
    // If response exists but isn't an array or expected structure, return empty array
    return response || [];
  } catch (error) {
    console.error('Failed to load material requests:', error);
    // Return null to trigger error state in component
    return null;
  }
}