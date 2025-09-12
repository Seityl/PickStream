import { useState, useCallback, useEffect } from 'react';
import { FaTimes, FaBarcode, FaCheck, FaSpinner, FaBox } from 'react-icons/fa';

type ScanAsBoxModalProps = {
  itemCode: string;
  requestedQuantity: string;
  uom: string;
  itemDescription: string;
  itemBarcode: string;
  setItemBarcode: (value: string) => void;
  validateBarcode: (itemCode: string, itemBarcode: string) => Promise<void>;
  itemIsValidated: boolean;
  submitScan: (options: {
    scannedQuantity: number;
    itemType: string;
  }) => Promise<void>;
  closeModal: () => void;
  isLoading?: boolean;
};

export default function ScanAsBoxModal({
  itemCode,
  requestedQuantity,
  uom,
  itemDescription,
  itemBarcode,
  setItemBarcode,
  validateBarcode,
  itemIsValidated,
  submitScan,
  closeModal,
  isLoading = false
}: ScanAsBoxModalProps) {
  const [scannedQuantity, setScannedQuantity] = useState<number>(0); 
  const [isValidatingBarcode, setIsValidatingBarcode] = useState(false);
  
  // Step management for better UX flow
  const [currentStep, setCurrentStep] = useState<'scan_barcode' | 'enter_quantity'>('scan_barcode');

  // Clear barcode when modal opens
  useEffect(() => {
    setItemBarcode('');
    setCurrentStep('scan_barcode');
  }, [setItemBarcode]);

  const handleBarcodeChange = (value: string) => {
    setItemBarcode(value);
  };

  const handleBarcodeValidation = useCallback(async () => {
    if (!itemBarcode.trim()) return;
    
    setIsValidatingBarcode(true);
    
    try {
      await validateBarcode(itemCode, itemBarcode);
      // Only progress to next step if validation succeeds
      setCurrentStep('enter_quantity');
    } catch (error) {
      console.error('Barcode validation failed:', error);
      // Set user-friendly error message
      // Don't change the step - stay on barcode scanning
      // Optionally clear the barcode input to allow re-scanning
      setItemBarcode('');
    } finally {
      setIsValidatingBarcode(false);
    }
  }, [validateBarcode, itemCode, itemBarcode, setItemBarcode]);
  
  const handleSubmitScan = useCallback(() => {
    submitScan({
      scannedQuantity, 
      itemType: "box"
    });
  }, [submitScan, scannedQuantity]);

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 backdrop-blur-md z-40" onClick={closeModal}></div>
      
      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-auto overflow-hidden border border-gray-200">
          
          {/* Header */}
          <div className="bg-orange-50 px-6 py-4 border-b border-orange-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <FaBox className="text-orange-600" size={16} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Scan as Box</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {itemCode} • Requested: {requestedQuantity} {uom}
                  </p>
                </div>
              </div>
              <button 
                onClick={closeModal}
                disabled={isLoading}
                className="p-2 hover:bg-orange-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FaTimes className="text-gray-500" size={16} />
              </button>
            </div>
          </div>

          {/* Progress Indicator */}
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${currentStep === 'scan_barcode' ? 'bg-orange-500' : itemIsValidated ? 'bg-green-500' : 'bg-gray-300'}`}></div>
              <span className="text-xs text-gray-600">Scan Barcode</span>
              <div className="flex-1 h-px bg-gray-300"></div>
              <div className={`w-3 h-3 rounded-full ${currentStep === 'enter_quantity' ? 'bg-orange-500' : 'bg-gray-300'}`}></div>
              <span className="text-xs text-gray-600">Enter Quantity</span>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 bg-white">
            
            {/* Step 1: Barcode Scanning */}
            {!itemIsValidated && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 rounded-full mb-4">
                    <FaBarcode className="text-orange-600" size={24} />
                  </div>
                  <p className="text-gray-600 mb-2">
                    Scan or enter the barcode for this item
                  </p>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
                    <p className="text-sm font-medium text-gray-900">{itemDescription}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="item_barcode" className="block text-sm font-medium text-gray-700">
                    Item Barcode
                  </label>
                  <input
                    id="item_barcode"
                    type="text"
                    placeholder="Scan barcode"
                    value={itemBarcode}
                    onChange={(e) => handleBarcodeChange(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none text-center font-mono"
                    autoFocus
                  />
                </div>

                <button 
                  onClick={handleBarcodeValidation}
                  disabled={!itemBarcode.trim() || isValidatingBarcode}
                  className="w-full bg-orange-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
                >
                  {isValidatingBarcode ? (
                    <>
                      <FaSpinner className="animate-spin" size={16} />
                      <span>Validating...</span>
                    </>
                  ) : (
                    <>
                      <FaCheck size={16} />
                      <span>Verify Barcode</span>
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Step 2: Quantity Entry */}
            {itemIsValidated && (
              <div className="space-y-6">
                
                {/* Item confirmation */}
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 text-green-800">
                    <FaCheck className="text-green-600" size={16} />
                    <span className="font-medium">Item Verified</span>
                  </div>
                  <p className="text-sm text-green-700 mt-1">{itemDescription}</p>
                </div>

                {/* Quantity Input */}
                <div className="space-y-2">
                  <label htmlFor="scanned_quantity" className="block text-sm font-medium text-gray-700">
                    Scanned Quantity
                  </label>
                  <input
                    id="scanned_quantity"
                    type="number"
                    min="1"
                    value={scannedQuantity || ''}
                    onChange={(e) => setScannedQuantity(parseInt(e.target.value) || 0)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none"
                    placeholder="Enter quantity"
                  />
                </div>

                {/* Info Note */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> This will be recorded as a box item scan.
                  </p>
                </div>

                {/* Submit Button */}
                <button
                  onClick={handleSubmitScan}
                  disabled={scannedQuantity === 0 || isLoading}
                  className="w-full bg-green-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
                >
                  {isLoading ? (
                    <>
                      <FaSpinner className="animate-spin" size={16} />
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <FaCheck size={16} />
                      <span>Submit Scan</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}