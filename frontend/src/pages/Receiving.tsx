import React, { useState } from 'react';
import { useLoaderData, useNavigate, Link } from 'react-router';
import { FaArrowLeft, FaPlus } from 'react-icons/fa';
import { ChevronDown, MapPin, Package, Tag, Scan } from 'lucide-react';
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
  console.log(receivingList);
  return { receivingList, user };
}

function ReceivingList() {
  const { receivingList, user } = useLoaderData() as { receivingList: ReceivingListType; user: string };
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'crates' | 'identifiers'>('crates');
  const [locationFilter, setLocationFilter] = useState('');
  const [scanInput, setScanInput] = useState('');
  const [receivedItems, setReceivedItems] = useState<(Crate | Identifier)[]>([]);

  // Debug: Log the receiving list data
  console.log('Receiving List Data:', receivingList);
  console.log('Crate Details:', receivingList?.crate_details);
  console.log('Identifier Details:', receivingList?.identifier_details);

  // Use real API data with fallback to empty arrays
  const effectiveCrates = receivingList?.crate_details || [];
  const effectiveIdentifiers = receivingList?.identifier_details || [];

  const crateCount = effectiveCrates.length;
  const identifierCount = effectiveIdentifiers.length;

  const currentItems = activeTab === 'crates' ? effectiveCrates : effectiveIdentifiers;
  
  const filteredItems = locationFilter 
    ? currentItems.filter(item => 
        item.source_warehouse.toLowerCase().includes(locationFilter.toLowerCase()) ||
        item.target_warehouse.toLowerCase().includes(locationFilter.toLowerCase())
      )
    : currentItems;

  // Get the scanned item if it exists and is eligible
  const scannedItem = scanInput.trim() 
    ? [...effectiveCrates, ...effectiveIdentifiers].find(item => {
        const code = 'crate_code' in item ? item.crate_code : item.identifier_code;
        return code.toLowerCase() === scanInput.trim().toLowerCase();
      })
    : null;

  // Check if the scanned item has already been received
  const isAlreadyReceived = scannedItem 
    ? receivedItems.some(item => {
        const itemCode = 'crate_code' in item ? item.crate_code : item.identifier_code;
        const scannedCode = 'crate_code' in scannedItem ? scannedItem.crate_code : scannedItem.identifier_code;
        return itemCode === scannedCode;
      })
    : false;

  const handleReceive = async () => {
    if (!scannedItem) return;

    if (isAlreadyReceived) {
      toast.error('Item has already been received.');
      return;
    }

    try {
      const isCrate = 'crate_code' in scannedItem;
      const code = isCrate ? scannedItem.crate_code : scannedItem.identifier_code;
      
      const params = {
        user,
        code: JSON.stringify(code),
        to_warehouse: scannedItem.target_warehouse,
        from_warehouse: scannedItem.source_warehouse
      };
      
      const response = await frappeClient.get('pick_stream.api.submit_receiving_request', params);
      
      setReceivedItems(prev => [scannedItem, ...prev]);
      toast.success(`${isCrate ? 'Crate' : 'Identifier'} ${code} has been successfully received.`);
      setScanInput('');

   
      if (response.message.data[1] === true && response.message.status === 200) {
        navigate(`/pick_stream/verification/${isCrate ? 'crate' : 'item'}/${code}`);
      }
    } catch (err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && scannedItem && !isAlreadyReceived) {
      handleReceive();
    }
  };

  return (
    <main className='min-h-screen bg-gray-50'>
      {/* Header */}
      <div className='bg-white border-b border-gray-200 px-4 py-4'>
        <div className='flex items-center justify-between mb-4'>
          <Link to={`/pick_stream/`} className='text-gray-600 hover:text-gray-800'>
            <FaArrowLeft size={20} />
          </Link>
        </div>
        
        {/* Title */}
        <div className='text-center mb-6'>
          <h1 className='text-2xl font-bold text-gray-900'>RECEIVING</h1>
        </div>
        
        {/* Scan Section */}
        <div className='mb-4'>
          <div className='flex items-center gap-2 mb-2'>
            <Scan className='text-gray-400' size={16} />
            <span className='text-sm font-medium text-gray-700'>Scan Item Code</span>
          </div>
          <div className='flex gap-2'>
            <input
              type='text'
              placeholder='Enter or scan item code...'
              value={scanInput}
              onChange={(e) => setScanInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className='flex-1 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              autoFocus
            />
            <button 
              onClick={handleReceive} 
              disabled={!scannedItem || isAlreadyReceived}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                scannedItem && !isAlreadyReceived
                  ? 'bg-gray-800 text-white hover:bg-gray-700'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }`}
            >
              Receive
            </button>
          </div>
          
          {/* Validation feedback */}
          {scanInput.trim() && (
            <div className='mt-2 text-sm'>
              {scannedItem ? (
                <div className={`p-3 rounded-lg ${
                  isAlreadyReceived 
                    ? 'bg-orange-50 text-orange-700 border border-orange-200' 
                    : 'bg-green-50 text-green-700 border border-green-200'
                }`}>
                  <p className='font-medium'>
                    {isAlreadyReceived ? '⚠️ Already Received' : '✅ Ready to Receive'}
                  </p>
                  <p className='text-xs mt-1'>
                    {'crate_code' in scannedItem ? `Crate ${scannedItem.crate_code}` : `Identifier ${scannedItem.identifier_code}`} - 
                    {scannedItem.source_warehouse} → {scannedItem.target_warehouse}
                  </p>
                </div>
              ) : (
                <div className='p-3 rounded-lg bg-red-50 text-red-700 border border-red-200'>
                  <p className='font-medium'>❌ Item not found</p>
                  <p className='text-xs mt-1'>Code "{scanInput}" is not eligible for receiving</p>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Location Filter */}
        <div className='mb-4'>
          <div className='relative'>
            <MapPin className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400' size={16} />
            <select 
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className='w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none'
            >
              <option value=''>Filter by location...</option>
              {currentItems.length > 0 && Array.from(new Set([...currentItems.map(item => item.source_warehouse), ...currentItems.map(item => item.target_warehouse)])).map(location => (
                <option key={location} value={location}>{location}</option>
              ))}
            </select>
            <ChevronDown className='absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400' size={16} />
          </div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className='bg-white border-b border-gray-200'>
        <div className='flex px-4'>
          <button
            onClick={() => setActiveTab('crates')}
            className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
              activeTab === 'crates'
                ? 'border-gray-800 text-gray-800'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Package size={16} />
            Crates ({crateCount})
          </button>
          <button
            onClick={() => setActiveTab('identifiers')}
            className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
              activeTab === 'identifiers'
                ? 'border-gray-800 text-gray-800'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Tag size={16} />
            Identifiers ({identifierCount})
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div className='p-4'>
        {/* Section Header */}
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden'>
          <div className='px-4 py-3 border-b border-gray-200'>
            <h2 className='flex items-center gap-2 font-semibold text-gray-800'>
              {activeTab === 'crates' ? <Package size={18} /> : <Tag size={18} />}
              {activeTab === 'crates' ? `Crates (${filteredItems.length})` : `Identifiers (${filteredItems.length})`}
            </h2>
          </div>
          
          {/* Table */}
          {filteredItems.length > 0 ? (
            <div className='overflow-x-auto'>
              <table className='w-full'>
                <thead className='bg-gray-50'>
                  <tr>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>Code</th>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>From</th>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>To</th>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>Status</th>
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {filteredItems.map((item) => {
                    const isCrate = 'crate_code' in item;
                    const code = isCrate ? item.crate_code : item.identifier_code;
                    const isReceived = receivedItems.some(received => {
                      const receivedCode = 'crate_code' in received ? received.crate_code : received.identifier_code;
                      return receivedCode === code;
                    });
                    return (
                      <tr key={code} className={isReceived ? 'bg-green-50' : ''}>
                        <td className='px-4 py-3 text-sm font-medium text-gray-900'>{code}</td>
                        <td className='px-4 py-3 text-sm text-gray-600'>{item.source_warehouse}</td>
                        <td className='px-4 py-3 text-sm text-gray-600'>{item.target_warehouse}</td>
                        <td className='px-4 py-3 text-sm'>
                          {isReceived ? (
                            <span className='inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800'>
                              Received
                            </span>
                          ) : (
                            <span className='inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800'>
                              Available
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className='px-4 py-8 text-center text-gray-500'>
              No {activeTab} found{locationFilter && ' for the selected location'}.
            </div>
          )}
        </div>
        
        {/* Recently Received Summary */}
        {receivedItems.length > 0 && (
          <div className='mt-4 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden'>
            <div className='px-4 py-3 border-b border-gray-200'>
              <h2 className='font-semibold text-gray-800'>Recently Received ({receivedItems.length})</h2>
            </div>
            <div className='p-4'>
              <div className='space-y-2 max-h-60 overflow-y-auto'>
                {receivedItems.slice(0, 5).map((item, index) => {
                  const isCrate = 'crate_code' in item;
                  const code = isCrate ? item.crate_code : item.identifier_code;
                  return (
                    <div key={`${code}-${index}`} className='flex items-center justify-between p-2 bg-gray-50 rounded'>
                      <div className='flex items-center gap-2'>
                        <span className='inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-800 font-mono'>
                          {code}
                        </span>
                        <span className='text-sm text-gray-600'>
                          {isCrate ? 'Crate' : 'Identifier'}
                        </span>
                      </div>
                      <span className='text-xs text-gray-500'>
                        Just now
                      </span>
                    </div>
                  );
                })}
                {receivedItems.length > 5 && (
                  <p className='text-xs text-center text-gray-500 pt-2'>
                    and {receivedItems.length - 5} more...
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default ReceivingList;
