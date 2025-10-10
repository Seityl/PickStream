import { useState, useCallback, useEffect } from 'react';
import { FaTimes, FaBarcode, FaPlus, FaCheck, FaSpinner } from 'react-icons/fa';

type CrateItem = {
  scanned_qty: number;
  crate_code: string;
  uom: string;
};

type SubmitScanOptions = {
  scannedQuantity: number;
  itemType: string;
  crates?: Array<{ scanned_qty: number; crate_code: string; uom: string }>;
};

type ScanItemModalProps = {
  itemCode: string;
  crateCode: string;
  requestedQuantity: string;
  uom: string;
  itemDescription: string;
  itemBarcode: string;
  setItemBarcode: (value: string) => void;
  validateBarcode: (itemCode: string, itemBarcode: string) => Promise<boolean>;
  validateCrate: (crateCode: string) => Promise<boolean>;
  itemIsValidated: boolean;
  submitScan: (options: SubmitScanOptions) => Promise<void>;
  closeModal: () => void;
  isLoading?: boolean;
  isLoadingActiveCrate?: boolean;
};

export default function ScanItemModal({
  itemCode,
  crateCode,
  requestedQuantity,
  uom,
  itemDescription,
  itemBarcode,
  setItemBarcode,
  validateBarcode,
  validateCrate,
  itemIsValidated,
  submitScan,
  closeModal,
  isLoading = false,
  isLoadingActiveCrate = false
}: ScanItemModalProps) {
  const [scannedQuantity, setScannedQuantity] = useState<number>(0);
  const [newCrateInput, setNewCrateInput] = useState<string>('');
  const [isAddingCrate, setIsAddingCrate] = useState(false);
  const [isValidatingCrate, setIsValidatingCrate] = useState(false);
  const [isValidatingBarcode, setIsValidatingBarcode] = useState(false);
  const [crates, setCrates] = useState<CrateItem[]>([{
    scanned_qty: 0,
    crate_code: crateCode,
    uom: uom || 'EACH'
  }]);

  // Step management for better UX flow
  const [currentStep, setCurrentStep] = useState<'scan_barcode' | 'enter_quantity' | 'add_crates'>('scan_barcode');

  // Clear barcode when modal opens (only once)
  useEffect(() => {
    setItemBarcode('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleBarcodeChange = (value: string) => {
    setItemBarcode(value);
  }
  const handleBarcodeValidation = useCallback(async () => {
    if (!itemBarcode.trim()) return;

    setIsValidatingBarcode(true);

    const isValid = await validateBarcode(itemCode, itemBarcode);

    if (isValid) {
      // Only progress to next step if validation succeeds
      setCurrentStep('enter_quantity');
    } else {
      // Clear the barcode input to allow re-scanning
      setItemBarcode('');
    }

    setIsValidatingBarcode(false);
  }, [validateBarcode, itemCode, itemBarcode, setItemBarcode]);

  const addNewCrate = useCallback(async () => {
    if (!newCrateInput.trim()) return;
    
    setIsValidatingCrate(true);
    try {
      const crateIsValid = await validateCrate(newCrateInput);
      
      if (crateIsValid && !crates.some(c => c.crate_code === newCrateInput)) {
        setCrates(prev => [...prev, {
          scanned_qty: 0,
          crate_code: newCrateInput,
          uom: uom || 'EACH'
        }]);
        setNewCrateInput('');
        setIsAddingCrate(false);
      }
    } catch (error) {
      console.error('Error validating crate:', error);
    } finally {
      setIsValidatingCrate(false);
    }
  }, [newCrateInput, validateCrate, crates, uom]);

  const handleQuantityChange = useCallback((index: number, value: string) => {
    const numValue = value === '' ? 0 : Number(value);
    if (!isNaN(numValue) && numValue >= 0) {
      const newCrates = [...crates];
      newCrates[index].scanned_qty = numValue;
      setCrates(newCrates);
    }
  }, [crates]);

  const handleSubmit = useCallback(() => {
    if (crates.length > 1) {
      submitScan({
        scannedQuantity: 0,
        crates: crates,
        itemType: "crates"
      });
    } else {
      submitScan({
        scannedQuantity: scannedQuantity,
        itemType: "crate"
      });
    }
  }, [submitScan, crates, scannedQuantity]);

  const getTotalScanned = () => {
    return crates.reduce((total, crate) => total + crate.scanned_qty, 0);
  };

  const isSubmitDisabled = () => {
    if (crates.length > 1) {
      return getTotalScanned() === 0;
    }
    return scannedQuantity === 0;
  };

  return (
    <>
      {/* Blurred Backdrop */}
      <div className="fixed inset-0 backdrop-blur-md z-40" onClick={closeModal}></div>
      
      {/* Modal with Solid Background */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-auto overflow-hidden border border-gray-200">
        
          {/* Header */}
          <div className="bg-blue-50 px-6 py-4 border-b border-blue-100">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Scan Item</h3>
                <p className="text-sm text-gray-600 mt-1">
                  {itemCode} • Requested: {requestedQuantity} {uom}
                </p>
              </div>
              <button 
                onClick={closeModal}
                className="p-2 hover:bg-blue-100 rounded-lg transition-colors"
              >
                <FaTimes className="text-gray-500" size={16} />
              </button>
            </div>
          </div>

          {/* Progress Indicator */}
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${currentStep === 'scan_barcode' ? 'bg-blue-500' : itemIsValidated ? 'bg-green-500' : 'bg-gray-300'}`}></div>
              <span className="text-xs text-gray-600">Scan Barcode</span>
              <div className="flex-1 h-px bg-gray-300"></div>
              <div className={`w-3 h-3 rounded-full ${currentStep === 'enter_quantity' || currentStep === 'add_crates' ? 'bg-blue-500' : 'bg-gray-300'}`}></div>
              <span className="text-xs text-gray-600">Enter Quantity</span>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 bg-white">
            
            {/* Step 1: Barcode Scanning */}
            {!itemIsValidated && (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                    <FaBarcode className="text-blue-600" size={24} />
                  </div>
                  <p className="text-gray-600 mb-2">
                    Scan the barcode for this item
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
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-center font-mono"
                    autoFocus
                  />
                </div>

                <button 
                  onClick={handleBarcodeValidation}
                  disabled={!itemBarcode.trim() || isValidatingBarcode}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
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

                {/* Crate Management */}
                {crates.length === 1 ? (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Crate Code
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={isLoadingActiveCrate ? 'Loading...' : crateCode}
                          readOnly
                          disabled={isLoadingActiveCrate}
                          className="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-lg text-gray-600 disabled:opacity-50"
                        />
                        {isLoadingActiveCrate && (
                          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <FaSpinner className="animate-spin text-blue-500" size={16} />
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Scan Quantity
                      </label>
                      <div className="relative">
                        <input
                          type="number"
                          min="0"
                          value={scannedQuantity || ''}
                          onChange={(e) => setScannedQuantity(Number(e.target.value) || 0)}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none pr-16"
                          placeholder="0"
                        />
                        <span className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">
                          {uom}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900">Multiple Crates</h4>
                      <span className="text-sm text-gray-600">
                        Total: {getTotalScanned()} {uom}
                      </span>
                    </div>
                    
                    <div className="border border-gray-200 rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Crate</th>
                            <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Qty</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {crates.map((crate, index) => (
                            <tr key={crate.crate_code} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-gray-900 font-mono">
                                {crate.crate_code}
                              </td>
                              <td className="px-4 py-3">
                                <div className="relative">
                                  <input
                                    type="number"
                                    min="0"
                                    value={crate.scanned_qty || ''}
                                    onChange={(e) => handleQuantityChange(index, e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none pr-12 text-sm"
                                    placeholder="0"
                                  />
                                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 text-xs">
                                    {crate.uom}
                                  </span>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Add Crate Section */}
                {!isAddingCrate ? (
                  <button
                    onClick={() => setIsAddingCrate(true)}
                    disabled={isLoadingActiveCrate}
                    className="w-full border-2 border-dashed border-gray-300 rounded-lg py-4 text-gray-600 hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <FaPlus size={16} />
                    <span>Add Another Crate</span>
                  </button>
                ) : (
                  <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                    <h5 className="font-medium text-gray-900">Add Crate</h5>
                    <div className="space-y-2">
                      <input
                        type="text"
                        placeholder="Scan crate code"
                        value={newCrateInput}
                        onChange={(e) => setNewCrateInput(e.target.value)}
                        disabled={isLoadingActiveCrate}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <div className="flex space-x-2">
                        <button
                          onClick={addNewCrate}
                          disabled={!newCrateInput.trim() || isValidatingCrate || isLoadingActiveCrate}
                          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-1"
                        >
                          {isValidatingCrate ? (
                            <>
                              <FaSpinner className="animate-spin" size={14} />
                              <span>Adding...</span>
                            </>
                          ) : (
                            <>
                              <FaPlus size={14} />
                              <span>Add</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setIsAddingCrate(false);
                            setNewCrateInput('');
                          }}
                          className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitDisabled() || isLoading}
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