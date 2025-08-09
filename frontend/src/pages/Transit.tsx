import React, { useState } from 'react';
import { useLoaderData, Link } from 'react-router';
import { FaArrowLeft, FaPlus } from 'react-icons/fa';
import { ChevronDown, MapPin, Package, Tag } from 'lucide-react';
import { getTransitListView } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import CreateTransitModal from '../components/CreateTransitModal';
import { frappeClient } from '../../utils/client';
import {toast} from 'react-toastify';

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

type TransitListType = {
  crate_details: Crate[];
  identifier_details: Identifier[];
};

export async function transitLoader() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Response("Not Logged In", { status: 401 });
  }
  const transitList = await getTransitListView(user);
  console.log(transitList);
  return { transitList, user };
}

function TransitList() {
  const { transitList, user } = useLoaderData() as { transitList: TransitListType; user: string };
  const [isCreateModalOpen, setCreateModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'crates' | 'identifiers'>('crates');
  const [locationFilter, setLocationFilter] = useState('');

  // Debug: Log the transit list data
  console.log('Transit List Data:', transitList);
  console.log('Crate Details:', transitList?.crate_details);
  console.log('Identifier Details:', transitList?.identifier_details);

  // Use real API data with fallback to empty arrays
  const effectiveCrates = transitList?.crate_details || [];
  const effectiveIdentifiers = transitList?.identifier_details || [];

  async function submitTransitRequest(selectedItems: { crates: Crate[]; identifiers: Identifier[] }) {
    const { crates, identifiers } = selectedItems;
    
    if (crates.length === 0 && identifiers.length === 0) {
      toast.error('Please select at least one item to transit');
      return;
    }

    // Group items by warehouse pairs
    const transitGroups = new Map<string, { crate_codes: string[]; identifier_codes: string[]; from_warehouse: string; to_warehouse: string }>();

    crates.forEach(crate => {
      const key = `${crate.source_warehouse}-${crate.target_warehouse}`;
      if (!transitGroups.has(key)) {
        transitGroups.set(key, {
          crate_codes: [],
          identifier_codes: [],
          from_warehouse: crate.source_warehouse,
          to_warehouse: crate.target_warehouse
        });
      }
      transitGroups.get(key)!.crate_codes.push(crate.crate_code);
    });

    identifiers.forEach(identifier => {
      const key = `${identifier.source_warehouse}-${identifier.target_warehouse}`;
      if (!transitGroups.has(key)) {
        transitGroups.set(key, {
          crate_codes: [],
          identifier_codes: [],
          from_warehouse: identifier.source_warehouse,
          to_warehouse: identifier.target_warehouse
        });
      }
      transitGroups.get(key)!.identifier_codes.push(identifier.identifier_code);
    });

    // Submit each group as a separate transit request
    try {
      for (const group of Array.from(transitGroups.values())) {
        const params = {
          user,
          from_warehouse: group.from_warehouse,
          to_warehouse: group.to_warehouse,
          crate_codes: group.crate_codes,
          identifier_codes: group.identifier_codes
        };
        
        await frappeClient.post('pick_stream.api.submit_transit_request', params);
        toast.success(`Transit created successfully from ${group.from_warehouse} to ${group.to_warehouse}!`);
      }
      setCreateModalOpen(false);
    } catch (err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    }
  }





  const crateCount = effectiveCrates.length;
  const identifierCount = effectiveIdentifiers.length;

  const currentItems = activeTab === 'crates' ? effectiveCrates : effectiveIdentifiers;
  
  const filteredItems = locationFilter 
    ? currentItems.filter(item => 
        item.source_warehouse.toLowerCase().includes(locationFilter.toLowerCase()) ||
        item.target_warehouse.toLowerCase().includes(locationFilter.toLowerCase())
      )
    : currentItems;


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
          <h1 className='text-2xl font-bold text-gray-900'>TRANSIT</h1>
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
        
        {/* Create Transit Button */}
        <button 
          onClick={() => setCreateModalOpen(true)}
          className='w-full bg-gray-800 text-white py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-gray-700 transition-colors'
        >
          <FaPlus size={14} />
          Create Transit
        </button>
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
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {filteredItems.map((item) => {
                    const isCrate = 'crate_code' in item;
                    const code = isCrate ? item.crate_code : item.identifier_code;
                    return (
                      <tr key={code}>
                        <td className='px-4 py-3 text-sm font-medium text-gray-900'>{code}</td>
                        <td className='px-4 py-3 text-sm text-gray-600'>{item.source_warehouse}</td>
                        <td className='px-4 py-3 text-sm text-gray-600'>{item.target_warehouse}</td>
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
      </div>
      <CreateTransitModal
        isOpen={isCreateModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreateTransit={submitTransitRequest}
        availableCrates={effectiveCrates}
        availableIdentifiers={effectiveIdentifiers}
      />
    </main>
  );
}

export default TransitList;
