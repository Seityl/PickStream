import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import { useAuth } from '../context/AuthContext';
import { useCrateDetails } from '../../utils/customApiHooks';
import { frappeClient } from '../../utils/client';
import { FaArrowLeft, FaBox, FaCheck, FaExclamationTriangle, FaTimes } from "react-icons/fa";
import { toast } from 'react-toastify';

interface CrateItem {
  item_code: string;
  item_name: string;
  uom: string;
  qty: number;
}

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  discrepancies: CrateItem[];
  totalItems: number;
  originalItems: any[];
}

function ConfirmationModal({ isOpen, onClose, onConfirm, discrepancies, totalItems, originalItems }: ConfirmationModalProps) {
  if (!isOpen) return null;

  const hasDiscrepancies = discrepancies.length > 0;
  return (
    <>
      <div className="fixed inset-0 backdrop-blur-md z-40" onClick={onClose}></div>
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-t-xl w-full max-w-md mx-auto max-h-[80vh] overflow-y-auto">
          <div className="p-6">
            <h3 className="text-xl font-semibold mb-4">Confirm Verification</h3>
            
            {hasDiscrepancies ? (
              <div className="mb-6">
                <div className="flex items-center mb-3 text-amber-600">
                  <FaExclamationTriangle className="mr-3 text-lg" />
                  <span className="font-medium">Quantity Discrepancies Found</span>
                </div>
                <p className="text-gray-600 mb-4">
                  {discrepancies.length} of {totalItems} items have quantity differences:
                </p>
                <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3 space-y-2">
                  {discrepancies.map((item) => {
                    const originalItem = originalItems.find((orig: any) => orig.item_code === item.item_code);
                    return (
                      <div key={item.item_code} className="text-sm">
                        <div className="font-medium">{item.item_code}</div>
                        <div className="text-gray-600">
                          Original: {originalItem?.qty} → Verified: {item.qty}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="flex items-center mb-6 text-green-600">
                <FaCheck className="mr-3 text-lg" />
                <span>All quantities confirmed.</span>
              </div>
            )}

            <div className="space-y-3">
              <button
                onClick={onConfirm}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                {hasDiscrepancies ? 'Confirm with Discrepancies' : 'Confirm Verification'}
              </button>
              <button
                onClick={onClose}
                className="w-full py-3 px-4 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function CrateVerification() {
  const navigate = useNavigate();
  const { crate_code } = useParams<{ crate_code: string }>();
  const { user } = useAuth();
  const { data: crateDetailsResponse, error, isLoading } = useCrateDetails(user || '', crate_code || '');
  const crateDetails = crateDetailsResponse?.data;
  const [items, setItems] = useState<CrateItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  
  useEffect(() => {
    if (crateDetails?.items) {
      const itemsWithNumericQty = crateDetails.items.map((item: any) => ({
        ...item,
        qty: Number(item.qty)
      }));
      setItems(itemsWithNumericQty);
    }
  }, [crateDetails]);
  
  const getItemStatus = (item: CrateItem) => {
    const originalItem = crateDetails?.items?.find((orig: any) => orig.item_code === item.item_code);
    if (!originalItem) return 'pending';
    if (item.qty === Number(originalItem.qty)) return 'complete';
    if (item.qty < Number(originalItem.qty)) return 'short';
    if (item.qty > Number(originalItem.qty)) return 'over';
    return 'pending';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete': return <FaCheck className="text-green-600 text-sm" />;
      case 'short': return <FaExclamationTriangle className="text-red-600 text-sm" />;
      case 'over': return <FaExclamationTriangle className="text-amber-600 text-sm" />;
      default: return <FaTimes className="text-gray-400 text-sm" />;
    }
  };

  async function submitVerificationRequest() {
    setIsSubmitting(true);
    try {
      const params = { user, crate_code, items };
      await frappeClient.post('pick_stream.api.submit_verification_request', params);
      toast.success("Verification submitted successfully");
      navigate('/pick_stream/verification');
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

  const handleConfirmVerification = () => {
    setShowConfirmation(false);
    submitVerificationRequest();
  };

  const updateQuantity = (index: number, newValue: number) => {
    const newItems = [...items];
    newItems[index].qty = Math.max(0, newValue);
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

  if (!crateDetails || items.length === 0) {
    return (
      <main className="flex flex-col">
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center space-x-4">
                <Link 
                  to="/pick_stream/verification"
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <FaArrowLeft size={20} className="text-gray-600" />
                </Link>
                <h1 className="text-xl font-semibold text-gray-900">Crate Verification</h1>
              </div>
            </div>
          </div>
        </div>
        <div className="flex-grow flex items-center justify-center p-6">
          <div className="text-center">
            <div className="p-4 bg-gray-100 rounded-full mb-4 inline-block">
              <FaBox className="text-gray-400" size={32} />
            </div>
            <p className="text-lg font-semibold mb-2">No Items Found</p>
            <p className="text-sm text-gray-500">This crate appears to be empty or the items couldn't be loaded.</p>
          </div>
        </div>
      </main>
    );
  }

  const discrepancies = items.filter(item => getItemStatus(item) !== 'complete');
  const hasDiscrepancies = discrepancies.length > 0;
  
  return (
    <main>
      {/* Header Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-4">
              <Link 
                to="/pick_stream/verification"
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </Link>
              <div className="flex items-center space-x-3">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">{crateDetails?.crate_code}</h1>
                  <p className="text-sm text-gray-500">{crateDetails.from_warehouse} → {crateDetails.to_warehouse}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4">
        <div className="space-y-3 mb-6">
          {items.map((item, index) => {
            const status = getItemStatus(item);
            const originalItem = crateDetails?.items?.find((orig: any) => orig.item_code === item.item_code);
            
            return (
              <div key={item.item_code} className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0 mr-3">
                    <div className="font-medium text-base mb-1">{item.item_code}</div>
                    <div className="text-sm text-gray-600 line-clamp-2 mb-1">{item.item_name}</div>
                    <div className="text-xs text-gray-500 bg-gray-100 inline-block px-2 py-1 rounded">
                      {item.uom}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {getStatusIcon(status)}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="text-center p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500 mb-1">Original</div>
                    <div className="font-semibold text-lg">{originalItem?.qty}</div>
                  </div>
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="text-xs text-gray-500 mb-1">Verified</div>
                    <div className="font-semibold text-lg text-blue-700">{item.qty}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => updateQuantity(index, item.qty - 1)}
                    disabled={item.qty <= 0}
                    className="w-12 h-12 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 flex items-center justify-center text-xl font-semibold active:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    −
                  </button>
                  <input
                    type="number"
                    value={item.qty}
                    onChange={(e) => updateQuantity(index, parseInt(e.target.value) || 0)}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-center text-lg font-semibold focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    min="0"
                  />
                  <button
                    onClick={() => updateQuantity(index, item.qty + 1)}
                    className="w-12 h-12 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 flex items-center justify-center text-xl font-semibold active:bg-gray-300"
                  >
                    +
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="p-4">
        <button 
          className="w-full py-4 px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={() => setShowConfirmation(true)}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Submitting...
            </span>
          ) : (
            hasDiscrepancies ? `Review & Submit (${discrepancies.length})` : 'Complete Verification'
          )}
        </button>
      </div>

      <ConfirmationModal
        isOpen={showConfirmation}
        onClose={() => setShowConfirmation(false)}
        onConfirm={handleConfirmVerification}
        discrepancies={discrepancies}
        totalItems={items.length}
        originalItems={crateDetails?.items || []}
      />
    </main>
  );
}

export default CrateVerification;