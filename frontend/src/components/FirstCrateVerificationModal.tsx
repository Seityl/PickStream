import { useState, useEffect } from 'react';
import { FaCheck, FaExclamationTriangle, FaTimes } from 'react-icons/fa';

interface CrateItem {
  name: string;
  item_code: string;
  item_name: string;
  uom: string;
  requested_qty: number;
  qty: number;
  final_qty: number;
}

interface FirstCrateData {
  crate_code: string;
  from_warehouse: string;
  to_warehouse: string;
  items: CrateItem[];
  requires_verification: boolean;
}

interface FirstCrateVerificationModalProps {
  crateData: FirstCrateData;
  onConfirm: (items: CrateItem[]) => Promise<void>;
  isLoading: boolean;
}

function FirstCrateVerificationModal({
  crateData,
  onConfirm,
  isLoading
}: FirstCrateVerificationModalProps) {
  const [items, setItems] = useState<CrateItem[]>([]);
  const [showConfirmation, setShowConfirmation] = useState(false);

  useEffect(() => {
    if (crateData?.items) {
      const enhancedItems = crateData.items.map((item: any) => ({
        ...item,
        requested_qty: item.requested_qty || item.qty,
        final_qty: item.qty,
      }));
      setItems(enhancedItems);
    }
  }, [crateData]);

  const getItemStatus = (item: CrateItem) => {
    if (item.final_qty === item.requested_qty) return 'complete';
    if (item.final_qty < item.requested_qty) return 'short';
    if (item.final_qty > item.requested_qty) return 'over';
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

  const updateQuantity = (index: number, newValue: number) => {
    const newItems = [...items];
    newItems[index].final_qty = Math.max(0, newValue);
    setItems(newItems);
  };

  const handleConfirm = () => {
    setShowConfirmation(false);
    onConfirm(items);
  };

  const discrepancies = items.filter(item => getItemStatus(item) !== 'complete');
  const hasDiscrepancies = discrepancies.length > 0;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 backdrop-blur-md z-50"></div>

      {/* Main Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-auto max-h-[90vh] overflow-hidden flex flex-col">

          {/* Header */}
          <div className="bg-blue-600 px-6 py-4 text-white">
            <h2 className="text-xl font-semibold">Verify First Crate</h2>
            <p className="text-sm text-blue-100 mt-1">
              {crateData.crate_code} • {crateData.from_warehouse} → {crateData.to_warehouse}
            </p>
          </div>

          {/* Info Banner */}
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-3">
            <p className="text-sm text-amber-800">
              <FaExclamationTriangle className="inline mr-2" />
              Please verify the quantities in the first crate before continuing.
            </p>
          </div>

          {/* Items List - Scrollable */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <div className="space-y-3">
              {items.map((item, index) => {
                const status = getItemStatus(item);
                return (
                  <div key={item.name} className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
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

                    <div className="grid grid-cols-3 gap-2 mb-4">
                      <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">Requested</div>
                        <div className="font-semibold text-lg">{item.requested_qty}</div>
                      </div>
                      <div className="text-center p-3 bg-blue-50 rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">Scanned</div>
                        <div className="font-semibold text-lg text-blue-700">{item.qty}</div>
                      </div>
                      <div className="text-center p-3 bg-green-50 rounded-lg">
                        <div className="text-xs text-gray-500 mb-1">Final</div>
                        <div className="font-semibold text-lg text-green-700">{item.final_qty}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => updateQuantity(index, item.final_qty - 1)}
                        className="w-12 h-12 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 flex items-center justify-center text-xl font-semibold active:bg-gray-300"
                      >
                        −
                      </button>
                      <input
                        type="number"
                        value={item.final_qty}
                        onChange={(e) => updateQuantity(index, parseInt(e.target.value) || 0)}
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-center text-lg font-semibold focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                        min="0"
                      />
                      <button
                        onClick={() => updateQuantity(index, item.final_qty + 1)}
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

          {/* Footer Actions */}
          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 space-y-3">
            <button
              onClick={() => setShowConfirmation(true)}
              disabled={isLoading}
              className="w-full py-4 px-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {hasDiscrepancies ? `Review & Confirm (${discrepancies.length} discrepancies)` : 'Confirm Quantities'}
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <>
          <div className="fixed inset-0 backdrop-blur-md z-60" onClick={() => setShowConfirmation(false)}></div>
          <div className="fixed inset-0 flex items-center justify-center z-60 p-4">
            <div className="bg-white rounded-xl w-full max-w-md mx-auto max-h-[80vh] overflow-y-auto shadow-2xl">
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-4">Confirm Verification</h3>

                {hasDiscrepancies ? (
                  <div className="mb-6">
                    <div className="flex items-center mb-3 text-amber-600">
                      <FaExclamationTriangle className="mr-3 text-lg" />
                      <span className="font-medium">Quantity Discrepancies Found</span>
                    </div>
                    <p className="text-gray-600 mb-4">
                      {discrepancies.length} of {items.length} items have quantity differences:
                    </p>
                    <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3 space-y-2">
                      {discrepancies.map((item) => (
                        <div key={item.name} className="text-sm">
                          <div className="font-medium">{item.item_code}</div>
                          <div className="text-gray-600">
                            Requested: {item.requested_qty} → Final: {item.final_qty}
                          </div>
                        </div>
                      ))}
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
                    onClick={handleConfirm}
                    disabled={isLoading}
                    className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Processing...' : hasDiscrepancies ? 'Confirm with Discrepancies' : 'Confirm'}
                  </button>
                  <button
                    onClick={() => setShowConfirmation(false)}
                    disabled={isLoading}
                    className="w-full py-3 px-4 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

export default FirstCrateVerificationModal;
