// Handle scan input
  const handleScanSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedInput = scanInput.trim();
    
    if (!trimmedInput) {
      setScanError('Please enter a code to scan');
      return;
    }

    const foundItem = itemLookup[trimmedInput.toLowerCase()];
    
    if (!foundItem) {
      setScanError(`Code "${trimmedInput}" not found in receiving queue`);
      setTimeout(() => setScanError(''), 3000);
      return;
    }

    // Use the unified receive function
    await handleReceiveItem(foundItem.item);
    setScanInput('');
    setScanError('');
  };import React, { useState, useRef } from 'react';
import { useLoaderData, useNavigate, Link } from 'react-router';
import { FaArrowLeft, FaBox, FaTag, FaSearch, FaTimes, FaCheck, FaMapMarkerAlt } from 'react-icons/fa';
import { getReceivingListView } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import { frappeClient } from '../../utils/client';
import { toast } from 'react-toastify';

type Identifier = {
  identifier_code: string;
  source_warehouse: string;
  target_warehouse: string;
};

type Crate = {
  crate_code: string;
  source_warehouse: string;
  target_warehouse: string;
};

type ReceivingListType = {
  crate_details: Crate[];
  identifier_details: Identifier[];
};

export async function receivingLoader() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Response("Not Logged In", { status: 401 });
  }
  const receivingList = await getReceivingListView(user);
  return { receivingList, user };
}

function ReceivingList() {
  const { receivingList, user } = useLoaderData() as { receivingList: ReceivingListType; user: string };
  const navigate = useNavigate();
  
  // Use real API data with fallback to empty arrays
  const effectiveCrates = receivingList?.crate_details || [];
  const effectiveIdentifiers = receivingList?.identifier_details || [];

  const crateCount = effectiveCrates.length;
  const identifierCount = effectiveIdentifiers.length;
  const totalCount = crateCount + identifierCount;

  // Group items by target warehouse, then by source warehouse
  const groupedByTarget = [...effectiveCrates, ...effectiveIdentifiers].reduce((acc, item) => {
    if (!acc[item.target_warehouse]) {
      acc[item.target_warehouse] = {};
    }
    if (!acc[item.target_warehouse][item.source_warehouse]) {
      acc[item.target_warehouse][item.source_warehouse] = [];
    }
    acc[item.target_warehouse][item.source_warehouse].push(item);
    return acc;
  }, {} as Record<string, Record<string, (Crate | Identifier)[]>>);

  const targetWarehouses = Object.keys(groupedByTarget).sort();
  const [activeTab, setActiveTab] = useState(targetWarehouses[0] || '');
  
  // Scan input state
  const [scanInput, setScanInput] = useState('');
  const [showScanInput, setShowScanInput] = useState(false);
  const [scanError, setScanError] = useState('');
  const [isReceiving, setIsReceiving] = useState(false);
  const scanInputRef = useRef<HTMLInputElement>(null);
  const [receivedItems, setReceivedItems] = useState<(Crate | Identifier)[]>([]);

  // Create a lookup map for quick searching
  const allItems = [...effectiveCrates, ...effectiveIdentifiers];
  const itemLookup = allItems.reduce((acc, item) => {
    const isCrate = 'crate_code' in item;
    const code = isCrate ? item.crate_code : item.identifier_code;
    acc[code.toLowerCase()] = {
      code,
      type: isCrate ? 'crate' : 'item',
      item
    };
    return acc;
  }, {} as Record<string, { code: string; type: 'crate' | 'item'; item: Crate | Identifier }>);

  // Handle receiving an item (from scan or list selection)
  const handleReceiveItem = async (selectedItem: Crate | Identifier) => {
    const isCrate = 'crate_code' in selectedItem;
    const code = isCrate ? selectedItem.crate_code : selectedItem.identifier_code;

    // Check if already received
    const isAlreadyReceived = receivedItems.some(item => {
      const itemCode = 'crate_code' in item ? item.crate_code : item.identifier_code;
      return itemCode === code;
    });

    if (isAlreadyReceived) {
      toast.error(`${isCrate ? 'Crate' : 'Item'} ${code} has already been received`);
      return;
    }

    // Proceed with receiving
    setIsReceiving(true);
    try {
      const params = {
        user,
        code: JSON.stringify(code),
        to_warehouse: selectedItem.target_warehouse,
        from_warehouse: selectedItem.source_warehouse
      };
      
      const response = await frappeClient.get('pick_stream.api.submit_receiving_request', params);
      
      setReceivedItems(prev => [selectedItem, ...prev]);
      toast.success(`${isCrate ? 'Crate' : 'Item'} ${code} received successfully`);

      if (response.message.data[1] === true && response.message.status === 200) {
        navigate(`/pick_stream/verification/${isCrate ? 'crate' : 'item'}/${code}`);
      }
    } catch (err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    } finally {
      setIsReceiving(false);
    }
  };

  // Toggle scan input
  const toggleScanInput = () => {
    setShowScanInput(!showScanInput);
    setScanInput('');
    setScanError('');
    if (!showScanInput) {
      setTimeout(() => scanInputRef.current?.focus(), 100);
    }
  };

  // Handle scan input changes
  const handleScanInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setScanInput(e.target.value);
    if (scanError) {
      setScanError('');
    }
  };

  return (
    <main className='min-h-screen bg-gray-50'>
      <header className='flex flex-row items-center px-4 py-4 bg-white shadow-sm border-b border-gray-200'>
        <Link 
          to={`/pick_stream/`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-3"
        >
          <FaArrowLeft size={20} className="text-gray-700"/>
        </Link>
        <div className="flex-1">
          <h1 className='text-lg font-semibold text-gray-900'>Receiving Queue</h1>
          <p className='text-sm text-gray-500 mt-1'>
            {totalCount} items ready for receiving
          </p>
        </div>
        <button
          onClick={toggleScanInput}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label={showScanInput ? "Close scan input" : "Open scan input"}
        >
          {showScanInput ? (
            <FaTimes size={20} className="text-gray-700" />
          ) : (
            <FaSearch size={20} className="text-gray-700" />
          )}
        </button>
      </header>

      {/* Scan Input */}
      {showScanInput && (
        <div className="bg-white border-b border-gray-200 px-4 py-4">
          <form onSubmit={handleScanSubmit} className="space-y-3">
            <div>
              <label htmlFor="scan-input" className="block text-sm font-medium text-gray-700 mb-2">
                Scan or enter item code
              </label>
              <div className="flex gap-2">
                <input
                  ref={scanInputRef}
                  id="scan-input"
                  type="text"
                  value={scanInput}
                  onChange={handleScanInputChange}
                  placeholder="Enter crate or item code..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                  autoComplete="off"
                  disabled={isReceiving}
                />
                <button
                  type="submit"
                  disabled={!scanInput.trim() || isReceiving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {isReceiving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Receiving...
                    </>
                  ) : (
                    'Receive'
                  )}
                </button>
              </div>
            </div>
            {scanError && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {scanError}
              </div>
            )}
          </form>
        </div>
      )}

      {totalCount === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 px-4">
          <div className="p-4 bg-gray-100 rounded-full mb-4">
            <FaBox className="text-gray-400" size={32} />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">All caught up!</h3>
          <p className="text-gray-500 text-center max-w-sm">
            No items are currently ready for receiving. New items will appear here when they're available.
          </p>
        </div>
      ) : (
        <>
          {/* Tab Navigation */}
          <div className="bg-white border-b border-gray-200">
            <nav className="px-4">
              <div className="flex space-x-8 overflow-x-auto">
                {targetWarehouses.map((warehouse) => {
                  const warehouseItems = Object.values(groupedByTarget[warehouse]).flat();
                  const itemCount = warehouseItems.length;
                  const isActive = activeTab === warehouse;
                  
                  return (
                    <button
                      key={warehouse}
                      onClick={() => setActiveTab(warehouse)}
                      className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm whitespace-nowrap transition-colors ${
                        isActive
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <FaMapMarkerAlt size={14} />
                      <span>{warehouse}</span>
                      <span className={`inline-flex items-center justify-center px-2 py-1 text-xs font-medium rounded-full ${
                        isActive 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {itemCount}
                      </span>
                    </button>
                  );
                })}
              </div>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="pb-20">
            {activeTab && groupedByTarget[activeTab] && (
              <div className="space-y-4 pt-4">
                {Object.entries(groupedByTarget[activeTab]).map(([sourceWarehouse, items]) => {
                  const routeCrateCount = items.filter(item => 'crate_code' in item).length;
                  const routeIdentifierCount = items.filter(item => 'identifier_code' in item).length;
                  
                  return (
                    <div key={sourceWarehouse} className="mx-4 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                      {/* Source Header */}
                      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <FaMapMarkerAlt className="text-gray-400 mr-2" size={16} />
                            <div>
                              <p className="text-sm font-medium text-gray-900">
                                From {sourceWarehouse}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3 text-xs text-gray-500">
                            {routeCrateCount > 0 && (
                              <span className="flex items-center">
                                <FaBox className="mr-1" size={12} />
                                {routeCrateCount}
                              </span>
                            )}
                            {routeIdentifierCount > 0 && (
                              <span className="flex items-center">
                                <FaTag className="mr-1" size={12} />
                                {routeIdentifierCount}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Items List */}
                      <div className="divide-y divide-gray-100">
                        {items.map((item) => {
                          const isCrate = 'crate_code' in item;
                          const code = isCrate ? item.crate_code : item.identifier_code;
                          const isReceived = receivedItems.some(received => {
                            const receivedCode = 'crate_code' in received ? received.crate_code : received.identifier_code;
                            return receivedCode === code;
                          });

                          return (
                            <div 
  key={code}
  onClick={() => !isReceived && !isReceiving && handleReceiveItem(item)}
  className={`px-4 py-3 transition-colors ${
    isReceived 
      ? 'bg-green-50' 
      : isReceiving 
        ? 'bg-gray-100 cursor-wait' 
        : 'hover:bg-blue-50 cursor-pointer'
  }`}
>
  <div className="flex items-center justify-between">
    <div className="flex items-center flex-1">
      <div className={`p-2 rounded-lg mr-3 border ${
        isCrate 
          ? 'bg-blue-50 border-blue-100' 
          : 'bg-green-50 border-green-100'
      }`}>
        {isCrate ? (
          <FaBox className="text-blue-600" size={16} />
        ) : (
          <FaTag className="text-green-600" size={16} />
        )}
      </div>
      
      <div className="flex-1">
        <span className="font-mono text-gray-900 font-medium text-base">
          {code}
        </span>
      </div>
    </div>
    
    {/* Type badge moved to the right side */}
    <div className="flex items-center ml-3">
      <span className={`px-2 py-1 text-xs font-medium rounded-md ${
        isCrate
          ? 'bg-blue-100 text-blue-800'
          : 'bg-green-100 text-green-800'
      }`}>
        {isCrate ? 'Crate' : 'Item'}
      </span>
    </div>
  </div>
</div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recently Received Summary */}
          {receivedItems.length > 0 && (
            <div className="fixed bottom-20 left-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
              <div className="bg-green-50 px-4 py-2 border-b border-green-200">
                <p className="text-sm font-medium text-green-800">
                  Recently Received ({receivedItems.length})
                </p>
              </div>
              <div className="p-3 max-h-32 overflow-y-auto">
                <div className="space-y-2">
                  {receivedItems.slice(0, 3).map((item, index) => {
                    const isCrate = 'crate_code' in item;
                    const code = isCrate ? item.crate_code : item.identifier_code;
                    return (
                      <div key={`${code}-${index}`} className="flex items-center text-sm">
                        <span className="font-mono text-gray-900 mr-2">{code}</span>
                        <span className="text-gray-500">•</span>
                        <span className="text-gray-600 ml-2">{isCrate ? 'Crate' : 'Item'}</span>
                      </div>
                    );
                  })}
                  {receivedItems.length > 3 && (
                    <p className="text-xs text-gray-500">
                      +{receivedItems.length - 3} more items
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}

export default ReceivingList;