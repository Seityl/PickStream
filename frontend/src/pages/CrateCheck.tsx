import { useState } from 'react';
import { Link } from 'react-router';
import { FaArrowLeft, FaBoxOpen, FaWarehouse, FaTimes, FaBarcode } from 'react-icons/fa';
import { toast } from 'react-toastify';
import { frappeClient } from '../../utils/client';

interface CrateItem {
  item_code: string;
  item_name: string;
  uom: string;
  requested_qty: number;
  scanned_qty: number;
  item_group: string;
}

interface CrateDetails {
  crate_code: string;
  color: string;
  status: string;
  from_warehouse: string;
  to_warehouse: string;
  items: CrateItem[];
  material_requests: string[];
  total_items: number;
}

export default function CrateCheck() {
  const [crateCode, setCrateCode] = useState('');
  const [crateDetails, setCrateDetails] = useState<CrateDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!crateCode.trim()) {
      toast.error('Please enter a crate code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const searchParams = { crate_code: crateCode.trim() };
      const response = await frappeClient.get('pick_stream.api.get_crate_check', searchParams);

      if (!response || !response.message) {
        throw new Error('Invalid API response');
      }

      if (response.message.status !== 200) {
        throw response.message;
      }

      setCrateDetails(response.message.data);
    } catch (err: any) {
      console.error('Error fetching crate details:', err);
      const errorMessage = err?.error?.error_message || err?.message || 'Failed to fetch crate details';
      setError(errorMessage);
      toast.error(errorMessage);
      setCrateDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeColor = (status: string) => {
    const statusColors: Record<string, string> = {
      'Available': 'bg-green-100 text-green-800',
      'Picking': 'bg-blue-100 text-blue-800',
      'Waiting': 'bg-yellow-100 text-yellow-800',
      'In Transit': 'bg-purple-100 text-purple-800',
      'Verified': 'bg-indigo-100 text-indigo-800',
      'Received': 'bg-gray-100 text-gray-800',
    };
    return statusColors[status] || 'bg-gray-100 text-gray-800';
  };

  const getColorBadge = (color: string) => {
    const colorStyles: Record<string, string> = {
      'Green': 'bg-green-500',
      'Gray': 'bg-gray-500',
      'Red': 'bg-red-500',
      'Yellow': 'bg-yellow-500',
      'Blue': 'bg-blue-500',
    };
    return colorStyles[color] || 'bg-gray-500';
  };

  return (
    <main>
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-4">
              <Link
                to="/pick_stream/tools"
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Crate Check</h1>
                <p className="text-sm text-gray-500">Scan or enter a crate code to view details</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        {/* Search Form */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Crate Code
              </label>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <FaBarcode className="text-gray-400" />
                  </div>
                  <input
                    type="text"
                    value={crateCode}
                    onChange={(e) => setCrateCode(e.target.value)}
                    placeholder="Enter or scan crate code"
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={loading}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || !crateCode.trim()}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <FaTimes className="text-red-600 mr-2" />
              <span className="text-red-800">{error}</span>
            </div>
          </div>
        )}

        {/* Crate Details */}
        {crateDetails && (
          <div className="space-y-6">
            {/* Summary Card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <FaBoxOpen className="text-blue-600" size={24} />
                  <h2 className="text-2xl font-bold text-gray-900">{crateDetails.crate_code}</h2>
                  <div className={`w-6 h-6 rounded-full ${getColorBadge(crateDetails.color)}`} title={crateDetails.color} />
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeColor(crateDetails.status)}`}>
                  {crateDetails.status}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="flex items-start space-x-3">
                  <FaWarehouse className="text-gray-400 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">From Warehouse</p>
                    <p className="font-semibold text-gray-900">{crateDetails.from_warehouse || 'N/A'}</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <FaWarehouse className="text-gray-400 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">To Warehouse</p>
                    <p className="font-semibold text-gray-900">{crateDetails.to_warehouse || 'N/A'}</p>
                  </div>
                </div>
              </div>

              {/* Progress Stats */}
                <div>
                  <p className="text-2xl font-bold text-gray-900">{crateDetails.total_items}</p>
                  <p className="text-sm text-gray-500">Total Items</p>
                </div>
            </div>

            {/* Material Requests */}
            {crateDetails.material_requests.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Material Requests</h3>
                <div className="flex flex-wrap gap-2">
                  {crateDetails.material_requests.map((mr) => (
                    <span
                      key={mr}
                      className="px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium"
                    >
                      {mr}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Items List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Items ({crateDetails.items.length})
              </h3>

              {crateDetails.items.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No items in this crate</p>
              ) : (
                <div className="space-y-3">
                  {crateDetails.items.map((item, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <p className="font-semibold text-gray-900">{item.item_code}</p>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{item.item_name}</p>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-gray-500">
                              <span className="font-medium">Group:</span> {item.item_group}
                            </span>
                            <span className="text-gray-500">
                              <span className="font-medium">UOM:</span> {item.uom}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500 mb-1">Quantity</div>
                          <div className="flex items-baseline gap-2">
                            <span className="text-2xl font-bold text-gray-900">{item.scanned_qty}</span>
                            {item.requested_qty && item.requested_qty !== item.scanned_qty && (
                              <span className="text-sm text-gray-500">/ {item.requested_qty}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}