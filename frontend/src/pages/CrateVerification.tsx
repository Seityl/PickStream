import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import { useAuth } from '../context/AuthContext';
import { useCrateDetails } from '../../utils/customApiHooks';
import { frappeClient } from '../../utils/client';
import { FaArrowLeft, FaBox, FaMapMarkerAlt, FaMinus, FaPlus, FaCheck, FaExclamationTriangle } from "react-icons/fa";
import { toast } from 'react-toastify';

function CrateVerification() {
  const navigate = useNavigate();
  const { crate_code } = useParams<{ crate_code: string }>();
  const { user } = useAuth();
  const { data: crateDetailsResponse, error, isLoading } = useCrateDetails(user || '', crate_code || '');
  const crateDetails = crateDetailsResponse?.data;
  const [items, setItems] = useState<any[]>([]); // Initialize as empty array
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Update items when crateDetails becomes available
  useEffect(() => {
    if (crateDetails?.items) {
      // Convert quantities to numbers to prevent string concatenation
      const itemsWithNumericQty = crateDetails.items.map((item: any) => ({
        ...item,
        qty: Number(item.qty)
      }));
      setItems(itemsWithNumericQty);
    }
  }, [crateDetails]);
  
  // Calculate verification summary
  const originalQuantity = crateDetails?.items?.reduce((sum: number, item: any) => sum + Number(item.qty), 0) || 0;
  const currentQuantity = items.reduce((sum, item) => sum + Number(item.qty), 0);
  const hasChanges = originalQuantity !== currentQuantity;
  const hasDiscrepancies = items.some(item => {
    const originalItem = crateDetails?.items?.find((orig: any) => orig.item_code === item.item_code);
    return originalItem && Number(originalItem.qty) !== Number(item.qty);
  });
  
  async function submitVerificationRequest() {
    setIsSubmitting(true);
    try {
      const params = { user, crate_code, items };

      const response = await frappeClient.post('pick_stream.api.submit_verification_request', params);

      toast.success("Verification submitted successfully");
      navigate('/pick_stream/verification'); // Navigate back to verification list
    }
    catch(err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const updateItemQuantity = (index: number, change: number) => {
    const newItems = [...items];
    newItems[index].qty = Math.max(0, Number(newItems[index].qty) + change);
    setItems(newItems);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600">Loading crate details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-50">
        <div className="p-4 bg-red-50 rounded-full mb-4">
          <FaExclamationTriangle className="text-red-500" size={32} />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Crate</h3>
        <p className="text-gray-600 text-center mb-4">Unable to load crate details. Please try again.</p>
        <Link 
          to="/pick_stream/verification"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Back to Verification List
        </Link>
      </div>
    );
  }
  
  return (
    <main className='bg-gray-50'>
      <header className='flex flex-row items-center px-4 py-4 bg-white shadow-sm border-b border-gray-200'>
        <Link 
          to="/pick_stream/verification"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-3"
        >
          <FaArrowLeft size={20} className="text-gray-700"/>
        </Link>
        <div className="flex-1">
          <h1 className='text-lg font-semibold text-gray-900 font-mono'>{crateDetails?.crate_code}</h1>
          {crateDetails && (
            <p className='text-sm text-gray-500 mt-1'>
              {crateDetails.from_warehouse} → {crateDetails.to_warehouse}
            </p>
          )}
        </div>
      </header>

      <div className='p-4'>
        {crateDetails && crateDetails.items?.length > 0 ? (
          <>
            {/* Items List */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <h2 className="text-sm font-medium text-gray-900">Items</h2>
              </div>
              
              <div className="divide-y divide-gray-100">
                {items.map((item, index) => {
                  const originalItem = crateDetails?.items?.find((orig: any) => orig.item_code === item.item_code);
                  const hasDiscrepancy = originalItem && Number(originalItem.qty) !== Number(item.qty);
                  
                  return (
                    <div key={item.item_code} className={`p-4 ${hasDiscrepancy ? 'bg-yellow-50' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0 mr-4">
                          <div className="flex items-center mb-1">
                            <p className="font-mono text-sm font-medium text-gray-900 mr-2">
                              {item.item_code}
                            </p>
                            {hasDiscrepancy && (
                              <div className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full">
                                Changed
                              </div>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 truncate">{item.item_name}</p>
                          <div className="flex items-center space-x-4 mt-1">
                            <span className="text-xs text-gray-500">UOM: {item.uom}</span>
                            {hasDiscrepancy && (
                              <span className="text-xs text-yellow-600">
                                Original: {originalItem?.qty}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          <button
                            onClick={() => updateItemQuantity(index, -1)}
                            disabled={item.qty <= 0}
                            className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            aria-label="Decrease quantity"
                          >
                            <FaMinus size={12} className="text-gray-600" />
                          </button>
                          
                          <div className="min-w-[3rem] text-center">
                            <span className={`text-lg font-semibold ${
                              hasDiscrepancy ? 'text-yellow-600' : 'text-gray-900'
                            }`}>
                              {item.qty}
                            </span>
                          </div>
                          
                          <button
                            onClick={() => updateItemQuantity(index, 1)}
                            className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                            aria-label="Increase quantity"
                          >
                            <FaPlus size={12} className="text-gray-600" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Submit Button */}
            <div className="pb-4">
              <button 
                onClick={submitVerificationRequest}
                disabled={isSubmitting}
                className="w-full flex items-center justify-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Submitting...
                  </>
                ) : (
                  <>
                    <FaCheck className="mr-2" size={16} />
                    Complete Verification
                  </>
                )}
              </button>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="p-4 bg-gray-100 rounded-full mb-4">
              <FaBox className="text-gray-400" size={32} />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Items Found</h3>
            <p className="text-gray-500 text-center max-w-sm mb-4">
              This crate appears to be empty or the items couldn't be loaded.
            </p>
            <Link 
              to="/pick_stream/verification"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Back to Verification List
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}

export default CrateVerification;