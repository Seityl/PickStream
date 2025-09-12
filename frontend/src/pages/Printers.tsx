import { useState } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
} from 'react-router';
import { FaSpinner, FaPrint, FaTimes, FaInfoCircle, FaCheckCircle, FaArrowLeft } from "react-icons/fa";
import { getPrinterList } from '../../utils/api';
import { frappeClient } from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';

// Define interface for print request parameters
interface PrintRequestParams {
  mr_name: string | null;
  printer: string;
  user: string;
  item_code: string | null;
  item_type: string | null;
  qty: number;
  identifier?: string | null;
}

// Enhanced printer interface (simplified without location)
interface PrinterInfo {
  name: string;
  status?: 'online' | 'offline' | 'busy';
  capabilities?: string[];
}

function Printers() {
  const [searchParams] = useSearchParams();
  const itemCode = searchParams.get('item_code');
  const itemType = searchParams.get('item_type');
  const materialRequest = searchParams.get('mr_name');
  const quantity = searchParams.get('qty');
  const identifier = searchParams.get('id');
  
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedPrinter, setSelectedPrinter] = useState<string>('');
  const [numOfCopies, setNumOfCopies] = useState<number>(
    quantity && !isNaN(parseInt(quantity)) ? parseInt(quantity) : 1
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [inputError, setInputError] = useState('');

  const printers = useLoaderData() as string[];
  const navigate = useNavigate();

  function openPrintModal(printerName: string) {
    setSelectedPrinter(printerName);
    setModalOpen(true);
    setError('');
    setInputError('');
    // Reset to default quantity or previously scanned quantity
    setNumOfCopies(quantity && !isNaN(parseInt(quantity)) ? parseInt(quantity) : 1);
  }

  function closePrintModal() {
    setModalOpen(false);
    setError('');
    setInputError('');
  }

  function validateQuantity(value: number): boolean {
    if (value <= 0) {
      setInputError('Quantity must be greater than 0');
      return false;
    }
    if (value > 999) {
      setInputError('Quantity cannot exceed 999');
      return false;
    }
    setInputError('');
    return true;
  }

  function handleQuantityChange(value: string) {
    const numValue = parseInt(value) || 0;
    setNumOfCopies(numValue);
    if (value !== '') {
      validateQuantity(numValue);
    } else {
      setInputError('');
    }
  }

  async function sendPrintRequest(printerName: string, qty: number) {
    if (!validateQuantity(qty)) {
      return;
    }

    try {
      setIsLoading(true);
      setError('');
      
      const user = await getCurrentUser();
      
      if (!user) {
        setError('User not authenticated');
        return;
      }
      
      const params: PrintRequestParams = {
        mr_name: materialRequest,
        printer: printerName,
        user: user,
        item_code: itemCode,
        item_type: itemType,
        qty: qty,
      };

      if (identifier) {
        params.identifier = identifier;
      }
      
      const response = await frappeClient.get('pick_stream.api.submit_print_request', params);
      toast.success(`${qty} label${qty !== 1 ? 's' : ''} sent to ${printerName}`, {
        position: "bottom-right",
        autoClose: 3000,
      });
      closePrintModal();
      navigate(-1);
    } catch(err: any) {
      const errorMessage = err?.message?.error?.error_message || 
                          err?.message || 
                          'Failed to submit print request';
      
      setError(errorMessage);
      toast.error(errorMessage, {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="bg-gray-50">
      {/* Improved Header */}
      <header className='sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm'>
        <div className="px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <FaArrowLeft className="text-gray-600" size={18} />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Select Printer</h1>
                <p className="text-sm text-gray-600 mt-1">Choose a printer for your labels</p>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      {/* Print Context Card */}
      {(itemCode || materialRequest) && (
        <div className="px-4 py-4">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-md">
                    <FaPrint className="text-white" size={16} />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">Print Request Details</h3>
                    <p className="text-sm text-gray-600">Review your label information</p>
                  </div>
                </div>
                
                {/* Item Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {itemCode && (
                    <div className="bg-white rounded-lg px-4 py-3 border border-blue-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Item Code</span>
                        <div className="text-right">
                          <span className="text-sm font-mono font-bold text-gray-500 px-2 py-1 rounded">
                            {itemCode}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {itemType && (
                    <div className="bg-white rounded-lg px-4 py-3 border border-blue-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Item Type</span>
                        <div className="text-right">
                          <span className="text-sm font-mono font-bold text-gray-500 px-2 py-1 rounded">
                            {itemType}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {materialRequest && (
                    <div className="bg-white rounded-lg px-4 py-3 border border-blue-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Material Request</span>
                        <div className="text-right">
                          <span className="text-sm font-mono font-bold text-gray-500 px-2 py-1 rounded">
                            {materialRequest}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {quantity && (
                    <div className="bg-white rounded-lg px-4 py-3 border border-blue-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Requested Qty</span>
                        <div className="text-right">
                          <span className="text-sm font-mono font-bold text-gray-500 px-2 py-1 rounded">
                            {quantity}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Optional identifier */}
                {identifier && (
                  <div className="mt-3">
                    <div className="bg-white rounded-lg px-4 py-3 border border-blue-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Identifier</span>
                        <div className="text-right">
                          <span className="text-sm font-mono font-bold text-gray-500 px-2 py-1 rounded">
                            {identifier}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className='px-4 py-4'>
        {printers.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
            <FaInfoCircle className="text-gray-400 text-3xl mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Printers Available</h3>
            <p className="text-gray-600">Please contact your administrator to configure printers.</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Available Printers</h2>
              <span className="text-sm text-gray-500">{printers.length} found</span>
            </div>
            
            {printers.map((printer) => {
              return (
                <button 
                  key={printer}
                  className='w-full bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all duration-200 text-left group'
                  onClick={() => openPrintModal(printer)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                          <FaPrint className="text-blue-600" size={18} />
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">{printer}</h3>
                          <div className="flex items-center space-x-2 mt-1">
                            <div className="flex items-center space-x-1">
                              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                              <span className="text-xs text-green-600 font-medium">Ready</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Enhanced Modal */}
            {modalOpen && (
        <>
          <div className="fixed inset-0 backdrop-blur-md z-40" onClick={closePrintModal}></div>
          
          <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-auto">
              
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b border-gray-200">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Print Labels</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Printer: {selectedPrinter}
                  </p>
                </div>
                <button 
                  onClick={closePrintModal}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  disabled={isLoading}
                >
                  <FaTimes className="text-gray-500" size={16} />
                </button>
              </div>

              {/* Modal Content */}
              <div className="p-6">
                
                {/* Print Details Summary */}
                {(itemCode || materialRequest) && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center space-x-2 mb-3">
                      <FaPrint className="text-blue-600" size={16} />
                      <h4 className="text-sm font-semibold text-blue-900">Print Details</h4>
                    </div>
                    <div className="grid grid-cols-1 gap-3">
                      {itemCode && (
                        <div className="flex items-center justify-between bg-white rounded-md px-3 py-2 border border-blue-100">
                          <span className="text-sm font-medium text-gray-600">Item Code</span>
                          <span className="text-sm font-medium text-gray-600">{itemCode}</span>
                        </div>
                      )}
                      {itemType && (
                        <div className="flex items-center justify-between bg-white rounded-md px-3 py-2 border border-blue-100">
                          <span className="text-sm font-medium text-gray-600">Item Type</span>
                          <span className="text-sm font-medium text-gray-600">{itemType}</span>
                        </div>
                      )}
                      {materialRequest && (
                        <div className="flex items-center justify-between bg-white rounded-md px-3 py-2 border border-blue-100">
                          <span className="text-sm font-medium text-gray-600">Material Request</span>
                          <span className="text-sm font-medium text-gray-600">{materialRequest}</span>
                        </div>
                      )}
                      {quantity && (
                        <div className="flex items-center justify-between bg-white rounded-md px-3 py-2 border border-blue-100">
                          <span className="text-sm font-medium text-gray-600">Requested Quantity</span>
                          <span className="text-sm font-medium text-gray-600">{quantity}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Quantity Input */}
                <div className="space-y-2">
                  <label htmlFor="num_of_copies" className="block text-sm font-medium text-gray-700">
                    Number of Copies
                  </label>
                  <div className="relative">
                    <input
                      id="num_of_copies"
                      type="number"
                      min="1"
                      max="999"
                      placeholder="Enter quantity"
                      value={numOfCopies || ''}
                      onChange={(e) => handleQuantityChange(e.target.value)}
                      className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none ${
                        inputError ? 'border-red-300 bg-red-50' : 'border-gray-300'
                      }`}
                      autoFocus
                    />
                  </div>
                  {inputError && (
                    <p className="text-sm text-red-600 flex items-center space-x-1">
                      <FaInfoCircle size={12} />
                      <span>{inputError}</span>
                    </p>
                  )}
                </div>

                {/* Quick Quantity Buttons */}
                <div className="flex space-x-2 mt-4">
                  <span className="text-sm text-gray-600 py-2">Quick select:</span>
                  {[1, 5, 10, 25].map((qty) => (
                    <button
                      key={qty}
                      onClick={() => {
                        setNumOfCopies(qty);
                        setInputError('');
                      }}
                      className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      disabled={isLoading}
                    >
                      {qty}
                    </button>
                  ))}
                </div>

                {/* Error Display */}
                {error && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={closePrintModal}
                    className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                    disabled={isLoading}
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={() => sendPrintRequest(selectedPrinter, numOfCopies)}
                    disabled={isLoading || numOfCopies <= 0 || !!inputError}
                    className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center space-x-2"
                  >
                    {isLoading ? (
                      <>
                        <FaSpinner className="animate-spin" size={16} />
                        <span>Printing...</span>
                      </>
                    ) : (
                      <>
                        <FaPrint size={16} />
                        <span>Print {numOfCopies > 1 ? `${numOfCopies} Labels` : 'Label'}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

export default Printers;

export async function printersViewLoader() {
  return await getPrinterList();
}