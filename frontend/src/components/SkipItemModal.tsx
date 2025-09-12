import { useCallback } from 'react';
import { FaTimes, FaExclamationTriangle, FaSpinner, FaCheck } from 'react-icons/fa';

type SkipItemModalProps = {
  skipItem: () => Promise<void>;  
  closeModal: () => void;
  isLoading?: boolean;
  itemCode?: string;
  itemDescription?: string;
};

export default function SkipItemModal({ 
  skipItem, 
  closeModal, 
  isLoading = false,
  itemCode,
  itemDescription 
}: SkipItemModalProps) {
  
  const handleSkipItem = useCallback(() => {
    skipItem();
  }, [skipItem]);

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 backdrop-blur-md z-40" onClick={closeModal}></div>
      
      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-auto overflow-hidden border border-gray-200">
          
          {/* Header */}
          <div className="bg-red-50 px-6 py-4 border-b border-red-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <FaExclamationTriangle className="text-red-600" size={16} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Skip Item</h3>
                </div>
              </div>
              <button 
                onClick={closeModal}
                disabled={isLoading}
                className="p-2 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FaTimes className="text-gray-500" size={16} />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            
            {/* Warning Message */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <FaExclamationTriangle className="text-red-600" size={24} />
              </div>
              
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                Skip this item?
              </h4>
              
              <p className="text-gray-600 mb-4">
                This action will mark the item as skipped and move to the next item in the pick list.
              </p>

              {/* Item Details (if provided) */}
              {(itemCode || itemDescription) && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                  {itemCode && (
                    <p className="text-sm font-medium text-gray-900 mb-1">
                      Item: {itemCode}
                    </p>
                  )}
                  {itemDescription && (
                    <p className="text-sm text-gray-600">
                      {itemDescription}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-3">
              <button 
                onClick={closeModal}
                disabled={isLoading}
                className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              
              <button 
                onClick={handleSkipItem}
                disabled={isLoading}
                className="flex-1 bg-red-600 text-white px-4 py-3 rounded-lg font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <FaSpinner className="animate-spin" size={16} />
                    <span>Skipping...</span>
                  </>
                ) : (
                  <>
                    <FaCheck size={16} />
                    <span>Skip Item</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}