import { useParams, Link, useLoaderData, LoaderFunctionArgs } from 'react-router';
import { FaArrowLeft, FaArrowRight, FaCheckCircle, FaSpinner, FaBox, FaExclamationCircle } from "react-icons/fa";
import { getItemGroups } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

type MaterialRequest = {
  mr_name: string;
  source_warehouse: string | null;
  target_warehouse: string;
  item_group_availability: ItemGroup[]
};

type ItemGroup = {
  name: string;
  status: 'available' | 'already_picked' | 'no_stock';
  item_count: {
    completed: number;
    total: number;
  }
  crates: Crate[];
}

type Crate = {
  crate_code: string;
  status: string;
}

function ItemGroupsView() {
  const viewData: MaterialRequest | null = useLoaderData();
  const params = useParams();
  const materialRequest = params.material_request;

  // Loading state
  if (!viewData) {
    return (
      <main className='flex items-center justify-center'>
        <FaSpinner className='animate-spin text-2xl text-blue-500 mx-auto mb-3' />
      </main>
    );
  }

  // Calculate summary statistics - count available and already_picked item groups
  const relevantItemGroups = viewData.item_group_availability.filter(item => 
    item.status === 'available' || item.status === 'already_picked'
  );
  const totalItems = relevantItemGroups.length;
  const completedItems = relevantItemGroups.filter(item => 
    item.status === 'already_picked' || item.item_count.completed === item.item_count.total
  ).length;

  return (
    <main>
      {/* Header */}
      <header className='bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm'>
        <div className='px-4 sm:px-6 py-4'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-4'>
              <Link 
                to={`/pick_stream/material-requests`}
                className="p-2 -ml-2 rounded-lg hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all duration-200 group"
                aria-label="Back to material requests"
              >
                <FaArrowLeft size={16} className="text-gray-600 group-hover:text-gray-900 group-hover:translate-x-[-1px] transition-all duration-200"/>
              </Link>
              
              <div>
                <div className='flex items-baseline space-x-3'>
                  <h1 className='text-xl font-semibold text-gray-900'>{viewData.target_warehouse}</h1>
                  <span className='text-sm text-gray-500 font-medium'>•</span>
                  <span className='text-sm text-gray-600 font-medium'>{viewData.mr_name}</span>
                </div>
                <div className='flex items-center space-x-2 mt-1'>
                  <FaCheckCircle className='text-green-500 text-sm' />
                  <span className='text-sm text-gray-600 font-medium'>
                    {completedItems}/{totalItems} Pick Lists Completed
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Item Groups List */}
      <div className='px-4 py-4 sm:px-6 pb-8'>
        {viewData.item_group_availability.length > 0 ? (
          <div className='space-y-3'>
            {viewData.item_group_availability.map((itemGroup: ItemGroup, index: number) => {
              const isReadOnly = itemGroup.status !== 'available';
              const isAlreadyPicked = itemGroup.status === 'already_picked';
              const isNoStock = itemGroup.status === 'no_stock';

              const progress = itemGroup.item_count.total > 0 
                ? Math.round((itemGroup.item_count.completed / itemGroup.item_count.total) * 100) 
                : 0;
              
              const isComplete = itemGroup.item_count.completed === itemGroup.item_count.total;
              const hasStarted = itemGroup.item_count.completed > 0;

              // Helper function to get status label
              const getStatusLabel = () => {
                if (isAlreadyPicked) return 'Already Picked';
                if (isNoStock) return 'No Stock';
                return '';
              };

              const CardContent = (
                <div className='p-4'>
                  {/* Header */}
                  <div className='flex items-center justify-between mb-3'>
                    <div className='flex items-center space-x-3 min-w-0 flex-1'>
                      <div className={`flex-shrink-0 p-2 rounded-lg ${
                        isComplete && !isNoStock
                          ? 'bg-green-50' 
                          : hasStarted 
                            ? 'bg-blue-50' 
                            : isNoStock
                              ? 'bg-orange-50'
                              : 'bg-gray-50'
                      }`}>
                        {isComplete && !isNoStock ? (
                          <FaCheckCircle className="w-5 h-5 text-green-600" />
                        ) : isNoStock ? (
                          <FaExclamationCircle className="w-5 h-5 text-orange-600" />
                        ) : (
                          <FaBox className="w-5 h-5 text-blue-600" />
                        )}
                      </div>

                      <div className='min-w-0 flex-1'>
                        <h3 className='font-semibold text-gray-900 truncate text-base'>
                          {itemGroup.name}
                        </h3>
                        <div className='flex items-center space-x-2 mt-1'>
                          <span className={`text-sm font-medium ${
                            isComplete && !isNoStock
                              ? 'text-green-600'
                              : hasStarted
                                ? 'text-blue-600'
                                : 'text-gray-600'
                          }`}>
                            {itemGroup.item_count.completed}/{itemGroup.item_count.total} items
                          </span>
                          {progress > 0 && (
                            <span className='text-xs text-gray-500'>
                              • {progress}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className='flex items-center space-x-2'>
                      {isReadOnly && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          isAlreadyPicked 
                            ? 'bg-gray-100 text-gray-700' 
                            : 'bg-orange-100 text-orange-700'
                        }`}>
                          {getStatusLabel()}
                        </span>
                      )}
                      {!isReadOnly && hasStarted && !isComplete && (
                        <span className='px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full'>
                          In Progress
                        </span>
                      )}
                      {!isReadOnly && isComplete && (
                        <span className='px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full'>
                          Ready
                        </span>
                      )}
                      {!isReadOnly && (
                        <FaArrowRight className='w-4 h-4 text-gray-400' />
                      )}
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {itemGroup.item_count.total > 0 && !isNoStock && (
                    <div className='mb-3'>
                      <div className='bg-gray-100 rounded-full h-2 overflow-hidden'>
                        <div 
                          className={`h-full transition-all duration-300 ease-out ${
                            isComplete ? 'bg-green-500' : 'bg-blue-500'
                          }`}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Crates Section */}
                  {itemGroup.crates.length > 0 && (
                    <div className='border-t border-gray-100 pt-3'>
                      <div className='flex items-center justify-between mb-2'>
                        <span className='text-sm font-medium text-gray-700'>
                          Crates
                        </span>
                      </div>
                      
                      <div className='flex flex-wrap gap-2'>
                        {itemGroup.crates.slice(0, 4).map((crate: Crate, crateIndex: number) => (
                          <div 
                            key={crateIndex}
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200"
                          >
                            <span className='truncate max-w-[80px]'>{crate.crate_code}</span>
                          </div>
                        ))}
                        
                        {itemGroup.crates.length > 4 && (
                          <div className='inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200'>
                            +{itemGroup.crates.length - 4} more
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );

              return isReadOnly ? (
                <div
                  key={index}
                  className="block bg-gray-50 cursor-not-allowed rounded-xl border border-gray-200 shadow-sm opacity-70"
                >
                  {CardContent}
                </div>
              ) : (
                <Link 
                  key={index}
                  to={`/pick_stream/picking?mr_name=${materialRequest}&item_group=${itemGroup.name}`}
                  className="block transition-all duration-200 hover:translate-y-[-1px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:ring-offset-2 rounded-xl"
                >
                  <div className='bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-gray-300 transition-all duration-200 overflow-hidden'>
                    {CardContent}
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          /* Empty State */
          <div className='flex items-center justify-center min-h-[50vh]'>
            <div className='text-center max-w-md'>
              <div className='bg-white p-8 rounded-2xl shadow-sm border border-gray-200'>
                <div className='bg-green-50 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6'>
                  <FaCheckCircle className='text-green-500 text-3xl' />
                </div>
                
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                  All Items Picked!
                </h2>
                
                <p className='text-gray-600 mb-6 leading-relaxed'>
                  All pick lists for this material request have been completed.
                </p>

                <Link 
                  to="/pick_stream/material-requests"
                  className='inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors'
                >
                  Back to Requests
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}


export default ItemGroupsView;

export async function itemGroupsLoader({ params }: LoaderFunctionArgs) {
  try {
    const user = await getCurrentUser();
    const { material_request } = params;
    
    if (!user) {
      throw new Error('User not authenticated');
    }
    
    if (!material_request) {
      throw new Error('Material request ID is required');
    }
    
    const response = await getItemGroups(user, material_request);
    return response;
  } catch (error) {
    console.error('Failed to load item groups:', error);
    return null;
  }
}