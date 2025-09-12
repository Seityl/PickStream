import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { useSubmitVerification, useItemIdentifierDetails } from '../../utils/customApiHooks';
import { FaArrowLeft, FaTag, FaMinus, FaPlus, FaCheck, FaExclamationTriangle } from 'react-icons/fa';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import { frappeClient } from '../../utils/client';

function ItemVerification() {
  const { identifier_code } = useParams<{ identifier_code: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: itemDetailsResponse, error, isLoading } = useItemIdentifierDetails(identifier_code || '');
  const itemDetails = itemDetailsResponse?.data;
  const [quantity, setQuantity] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (itemDetails) {
      setQuantity(Number(itemDetails.qty));
    }
  }, [itemDetails]);

  // Check if quantity has changed
  const originalQuantity = Number(itemDetails?.qty) || 0;
  const hasDiscrepancy = originalQuantity !== Number(quantity);

  async function submitVerificationRequest() {
    setIsSubmitting(true);
    try {
      const params = { user, identifier_code, items: JSON.stringify([{...itemDetails, qty: quantity}]) };

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

  const updateQuantity = (change: number) => {
    setQuantity(Math.max(0, quantity + change));
  };

  if (isLoading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600">Loading item details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-50">
        <div className="p-4 bg-red-50 rounded-full mb-4">
          <FaExclamationTriangle className="text-red-500" size={32} />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Item</h3>
        <p className="text-gray-600 text-center mb-4">Unable to load item details. Please try again.</p>
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
    <main className='min-h-screen bg-gray-50'>
      <header className='flex flex-row items-center px-4 py-4 bg-white shadow-sm border-b border-gray-200'>
        <Link 
          to="/pick_stream/verification"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-3"
        >
          <FaArrowLeft size={20} className="text-gray-700"/>
        </Link>
        <div className="flex-1">
          <h1 className='text-lg font-semibold text-gray-900 font-mono'>{itemDetails?.item_code}</h1>
          {itemDetails && (
            <p className='text-sm text-gray-500 mt-1'>
              {itemDetails.from_warehouse} → {itemDetails.to_warehouse}
            </p>
          )}
        </div>
      </header>

      <div className='p-4'>
        {itemDetails ? (
          <>
            {/* Item Details Card */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <h2 className="text-sm font-medium text-gray-900">Item Details</h2>
              </div>
              
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 mr-4">
                    <div className="flex items-center mb-2">
                      <div className="p-2 bg-green-50 border border-green-100 rounded-lg mr-3">
                        <FaTag className="text-green-600" size={16} />
                      </div>
                      <div>
                        <p className="font-mono text-base font-medium text-gray-900">
                          {itemDetails.item_code}
                        </p>
                        {hasDiscrepancy && (
                          <div className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full mt-1 inline-block">
                            Changed
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="ml-11">
                      <p className="text-sm text-gray-600 mb-2">{itemDetails.item_name}</p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>UOM: {itemDetails.uom}</span>
                        {hasDiscrepancy && (
                          <span className="text-yellow-600">
                            Original: {originalQuantity}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Quantity Controls */}
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setQuantity(Math.max(0, Number(quantity) - 1))}
                      disabled={quantity <= 0}
                      className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Decrease quantity"
                    >
                      <FaMinus size={12} className="text-gray-600" />
                    </button>
                    
                    <div className="min-w-[3rem] text-center">
                      <span className={`text-lg font-semibold ${
                        hasDiscrepancy ? 'text-yellow-600' : 'text-gray-900'
                      }`}>
                        {quantity}
                      </span>
                    </div>
                    
                    <button
                      onClick={() => setQuantity(Number(quantity) + 1)}
                      className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                      aria-label="Increase quantity"
                    >
                      <FaPlus size={12} className="text-gray-600" />
                    </button>
                  </div>
                </div>
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
              <FaTag className="text-gray-400" size={32} />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Item Not Found</h3>
            <p className="text-gray-500 text-center max-w-sm mb-4">
              The requested item details could not be loaded or do not exist.
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

export default ItemVerification;