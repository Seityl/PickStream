import React, { useState, useRef } from 'react';
import { Link, useLoaderData, useNavigate } from 'react-router';
import { FaArrowLeft, FaBox, FaTag, FaMapMarkerAlt, FaSearch, FaTimes } from "react-icons/fa";
import { getVerificationListView } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import ListItem from '../components/ListItem';

type Identifier = {
  identifier_code: string;
  source_warehouse: string;
  target_warehouse: string
}

type Crate = {
  crate_code: string;
  source_warehouse: string;
  target_warehouse: string
}

type VerificationListType = {
  crate_details: Crate[];
  identifier_details: Identifier[];
};

export async function verificationLoader() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Response("Not Logged In", { status: 401 });
  }
  const verificationList = await getVerificationListView(user);
  return { verificationList };
}

function VerificationList() {
  const { verificationList } = useLoaderData() as { verificationList: VerificationListType };
  const navigate = useNavigate();

  const totalCount = verificationList.crate_details.length + verificationList.identifier_details.length;

  // Create a lookup map for quick searching
  const allItems = [...verificationList.crate_details, ...verificationList.identifier_details];
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

  // Group items by target warehouse, then by source warehouse
  const groupedByTarget = allItems.reduce((acc, item) => {
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
  const scanInputRef = useRef<HTMLInputElement>(null);

  // Handle scan input
  const handleScanSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedInput = scanInput.trim();
    
    if (!trimmedInput) {
      setScanError('Please enter a code to scan');
      return;
    }

    const foundItem = itemLookup[trimmedInput.toLowerCase()];
    
    if (foundItem) {
      // Navigate to verification page
      navigate(`/pick_stream/verification/${foundItem.type}/${foundItem.code}`);
    } else {
      setScanError(`Code "${trimmedInput}" not found in verification queue`);
      // Clear error after 3 seconds
      setTimeout(() => setScanError(''), 3000);
    }
  };

  // Toggle scan input
  const toggleScanInput = () => {
    setShowScanInput(!showScanInput);
    setScanInput('');
    setScanError('');
    if (!showScanInput) {
      // Focus input after it's rendered
      setTimeout(() => scanInputRef.current?.focus(), 100);
    }
  };

  // Handle scan input changes
  const handleScanInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setScanInput(e.target.value);
    if (scanError) {
      setScanError(''); // Clear error when user starts typing
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
          <h1 className='text-lg font-semibold text-gray-900'>Verification Queue</h1>
          <p className='text-sm text-gray-500 mt-1'>
            {totalCount} items awaiting verification
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
                  placeholder="Enter crate or identifier code..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                  autoComplete="off"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
                >
                  Go
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
            No items are currently awaiting verification. New items will appear here when they're ready for review.
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
          <div>
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
                          const type = isCrate ? 'crate' : 'item';
                          const linkTo = `/pick_stream/verification/${type}/${code}`;

                          return (
                            <Link 
                              to={linkTo} 
                              key={code}
                              className="block hover:bg-gray-50 transition-colors"
                            >
                              <div className="px-4 py-3">
                                <ListItem code={code} type={type} />
                              </div>
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </main>
  );
}

export default VerificationList;