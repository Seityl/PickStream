import React, { useState, useMemo } from 'react';
import { useLoaderData, Link } from 'react-router';
import { FaArrowLeft, FaPlus, FaSearch, FaTimes } from 'react-icons/fa';
import { ChevronDown, MapPin, Package, Tag } from 'lucide-react';
import { getTransitListView } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import CreateTransitModal from '../components/CreateTransitModal';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('');

  // Debug: Log the transit list data
  console.log('Transit List Data:', transitList);
  console.log('Crate Details:', transitList?.crate_details);
  console.log('Identifier Details:', transitList?.identifier_details);

  // Use real API data with fallback to empty arrays
  const effectiveCrates = transitList?.crate_details || [];
  const effectiveIdentifiers = transitList?.identifier_details || [];

  // Memoized filter options for better performance
  const filterOptions = useMemo(() => {
    const currentItems = activeTab === 'crates' ? effectiveCrates : effectiveIdentifiers;
    
    if (!currentItems || currentItems.length === 0) {
      return { locations: [] };
    }
    
    const locations = Array.from(new Set([
      ...currentItems.map(item => item?.source_warehouse).filter(Boolean),
      ...currentItems.map(item => item?.target_warehouse).filter(Boolean)
    ])).sort();

    return { locations };
  }, [activeTab, effectiveCrates, effectiveIdentifiers]);

  // Enhanced filtering with search
  const filteredItems = useMemo(() => {
    const currentItems = activeTab === 'crates' ? effectiveCrates : effectiveIdentifiers;
    
    if (!currentItems || currentItems.length === 0) {
      return [];
    }
    
    return currentItems.filter(item => {
      if (!item) return false;
      
      const code = 'crate_code' in item ? item.crate_code : item.identifier_code;
      const sourceWarehouse = item.source_warehouse || '';
      const targetWarehouse = item.target_warehouse || '';
      
      // Search filter
      const matchesSearch = !searchTerm || 
        (code && code.toLowerCase().includes(searchTerm.toLowerCase())) ||
        sourceWarehouse.toLowerCase().includes(searchTerm.toLowerCase()) ||
        targetWarehouse.toLowerCase().includes(searchTerm.toLowerCase());
      
      // Location filter
      const matchesLocation = !locationFilter ||
        sourceWarehouse === locationFilter ||
        targetWarehouse === locationFilter;
      
      return matchesSearch && matchesLocation;
    });
  }, [activeTab, effectiveCrates, effectiveIdentifiers, searchTerm, locationFilter]);

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

  const clearAllFilters = () => {
    setSearchTerm('');
    setLocationFilter('');
  };

  const hasActiveFilters = searchTerm || locationFilter;
  const crateCount = effectiveCrates.length;
  const identifierCount = effectiveIdentifiers.length;

  return (
    <main className='bg-gray-50'>
      {/* Header */}
      <header className='flex flex-row items-center px-4 py-4 bg-white shadow-sm border-b border-gray-200'>
        <Link 
          to={`/pick_stream/`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-3"
        >
          <FaArrowLeft size={20} className="text-gray-700"/>
        </Link>
        <div className="flex-1">
          <h1 className='text-lg font-semibold text-gray-900'>Transit Queue</h1>
          <p className='text-sm text-gray-500 mt-1'>
            {crateCount + identifierCount} available for transit
          </p>
        </div>
      </header>
      <div className='bg-white border-b border-gray-200 px-4 py-4'>
        
        {/* Search Bar */}
        <div className='mb-4'>
          <div className='relative'>
            <FaSearch className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400' size={16} />
            <input
              type='text'
              placeholder='Search by code or warehouse...'
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className='w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className='absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600'
              >
                <FaTimes size={14} />
              </button>
            )}
          </div>
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
              {filterOptions.locations.map(location => (
                <option key={location} value={location}>{location}</option>
              ))}
            </select>
            <ChevronDown className='absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400' size={16} />
          </div>
        </div>
        
        {/* Create Transit Button */}
        <button 
          onClick={() => setCreateModalOpen(true)}
          className='w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-blue-700 transition-colors shadow-sm'
        >
          <FaPlus size={14} />
          Create New Transit
        </button>
      </div>
      
      {/* Tabs */}
      <div className='bg-white border-b border-gray-200'>
        <div className='flex px-4'>
          <button
            onClick={() => setActiveTab('crates')}
            className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
              activeTab === 'crates'
                ? 'border-blue-600 text-blue-600'
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
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Tag size={16} />
            Identifiers ({identifierCount})
          </button>
        </div>
      </div>
      
      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className='bg-blue-50 border-b border-blue-200 px-4 py-3'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-2 text-sm text-blue-700'>
              {filteredItems.length} of {activeTab === 'crates' ? crateCount : identifierCount} {activeTab} shown
            </div>
            <button
              onClick={clearAllFilters}
              className='text-sm text-blue-600 hover:text-blue-800 transition-colors'
            >
              Clear filters
            </button>
          </div>
        </div>
      )}
      
      {/* Content */}
      <div className='p-4'>
        {/* Section Header */}
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden'>
          
          {/* Table */}
          {filteredItems.length > 0 ? (
            <div className='overflow-x-auto'>
              <table className='w-full'>
                <thead className='bg-gray-50'>
                  <tr>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      {activeTab === 'crates' ? 'Crate Code' : 'Identifier Code'}
                    </th>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>From</th>
                    <th className='px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>To</th>
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {filteredItems.map((item) => {
                    const isCrate = 'crate_code' in item;
                    const code = isCrate ? item.crate_code : item.identifier_code;
                    return (
                      <tr key={code} className='hover:bg-gray-50 transition-colors'>
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
            <div className='px-4 py-12 text-center'>
              <div className='text-gray-400 mb-3'>
                {activeTab === 'crates' ? <Package size={48} className='mx-auto' /> : <Tag size={48} className='mx-auto' />}
              </div>
              <p className='text-gray-500 text-lg font-medium mb-2'>
                No {activeTab} found
              </p>
              <p className='text-gray-400 text-sm'>
                {hasActiveFilters 
                  ? 'Try adjusting your search or filter criteria'
                  : `No ${activeTab} are currently available for transit`
                }
              </p>
              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className='mt-3 text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors'
                >
                  Clear all filters
                </button>
              )}
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