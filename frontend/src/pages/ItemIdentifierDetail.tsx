import React, { ReactNode } from 'react';
import { useParams, useNavigate, Link } from 'react-router';
import { FaArrowLeft, FaBarcode, FaPrint, FaBox, FaClipboardList, FaTruck, FaClock, FaUser } from 'react-icons/fa';
import { useItemIdentifierDetails } from '../../utils/customApiHooks';

interface ItemIdentifierDetails {
  item_code: string;
  item_type: string;
  uom: string;
  qty: number;
  material_request: string;
  from_warehouse: string;
  to_warehouse: string;
  date_created: string;
  printed: number;
  qty_printed: number;
  dates_printed: string;
  user: string;
}

interface InfoCardProps {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  children: ReactNode;
  iconColor?: string;
  bgColor?: string;
}

interface DataRowProps {
  label: string;
  value: string | number | null | undefined;
}

export default function ItemIdentifierDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data: response, isLoading, error } = useItemIdentifierDetails(id || '');
  
  const itemIdentifierDetails: ItemIdentifierDetails | undefined = response?.data;

  const InfoCard = ({ icon: Icon, title, children, iconColor = "text-blue-600", bgColor = "bg-blue-50" }: InfoCardProps) => (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center space-x-3 mb-4">
        <div className={`p-2 ${bgColor} rounded-lg`}>
          <Icon size={20} className={iconColor} />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  );

  const DataRow = ({ label, value }: DataRowProps) => (
    <div className="flex justify-between items-start py-2 border-b border-gray-100 last:border-b-0">
      <span className="font-medium text-gray-600 text-sm">{label}</span>
      <span className="text-gray-900 text-sm font-medium text-right ml-4">{value || 'N/A'}</span>
    </div>
  );

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center space-x-4 p-4">
              <button 
                onClick={() => navigate('/pick_stream/tools/identifier-lookup')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                type="button"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-50 rounded-lg">
                  <FaBarcode size={20} className="text-blue-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Loading...</h1>
                  <p className="text-sm text-gray-500">Please wait</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="max-w-4xl mx-auto p-4">
          <div className="animate-pulse space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-xl p-6 border border-gray-200">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
                <div className="space-y-2">
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center space-x-4 p-4">
              <button 
                onClick={() => navigate('/pick_stream/tools/identifier-lookup')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                type="button"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-red-50 rounded-lg">
                  <FaBarcode size={20} className="text-red-600" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Error Loading Data</h1>
                  <p className="text-sm text-gray-500">Unable to load identifier details</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="max-w-4xl mx-auto p-4">
          <div className="bg-white rounded-xl shadow-sm border border-red-200 p-12 text-center">
            <div className="p-4 bg-red-50 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
              <FaBarcode size={32} className="text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to Load</h3>
            <p className="text-gray-500 mb-6">There was an error loading the identifier details.</p>
            <button 
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              type="button"
            >
              Try Again
            </button>
          </div>
        </div>
      </main>
    );
  }
  
  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate('/pick_stream/tools/identifier-lookup')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                type="button"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </button>
              <div className="flex items-center space-x-3">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Identifier Details</h1>
                  <p className="text-sm text-gray-500">ID: {id}</p>
                </div>
              </div>
            </div>
            
            {/* Quick Actions */}
            {itemIdentifierDetails && (
              <div className="flex items-center space-x-2">
                <Link 
                  to={`/pick_stream/printers?mr_name=${itemIdentifierDetails.material_request}&item_code=${itemIdentifierDetails.item_code}&item_type=${itemIdentifierDetails.item_type}&id=${id}&qty=${itemIdentifierDetails.qty}`}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  <FaPrint size={16} />
                  <span className="hidden sm:inline">Print Identifier</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content Section */}
      <div className="max-w-4xl mx-auto p-4">
        {itemIdentifierDetails ? (
          <div className="grid gap-6">
            {/* Item Details Card */}
            <InfoCard icon={FaBox} title="Item Details" iconColor="text-green-600" bgColor="bg-green-50">
              <DataRow label="Item Code" value={itemIdentifierDetails.item_code} />
              <DataRow label="Item Type" value={itemIdentifierDetails.item_type} />
              <DataRow label="Unit of Measure" value={itemIdentifierDetails.uom} />
              <DataRow label="Quantity" value={itemIdentifierDetails.qty} />
            </InfoCard>

            {/* Material Request Card */}
            <InfoCard icon={FaClipboardList} title="Material Request" iconColor="text-purple-600" bgColor="bg-purple-50">
              <DataRow label="Request Number" value={itemIdentifierDetails.material_request} />
              <DataRow label="Created By" value={itemIdentifierDetails.user} />
            </InfoCard>

            {/* Transfer Details Card */}
            <InfoCard icon={FaTruck} title="Transfer Details" iconColor="text-orange-600" bgColor="bg-orange-50">
              <DataRow label="From Warehouse" value={itemIdentifierDetails.from_warehouse} />
              <DataRow label="To Warehouse" value={itemIdentifierDetails.to_warehouse} />
            </InfoCard>

            {/* Print History Card */}
            <InfoCard icon={FaPrint} title="Print History" iconColor="text-blue-600" bgColor="bg-blue-50">
              <DataRow label="Number of Print Jobs" value={itemIdentifierDetails.printed} />
              <DataRow label="Total Labels Printed" value={itemIdentifierDetails.qty_printed} />
              {itemIdentifierDetails.dates_printed && (
                <div className="py-2 border-b border-gray-100 last:border-b-0">
                  <span className="font-medium text-gray-600 text-sm block mb-2">Print History</span>
                  <div 
                    className="text-gray-900 text-xs bg-gray-50 p-3 rounded-lg font-mono"
                    dangerouslySetInnerHTML={{ __html: itemIdentifierDetails.dates_printed }}
                  />
                </div>
              )}
            </InfoCard>

            {/* Timestamps Card */}
            <InfoCard icon={FaClock} title="Timeline" iconColor="text-gray-600" bgColor="bg-gray-50">
              <DataRow label="Date Created" value={itemIdentifierDetails.date_created} />
            </InfoCard>

            {/* Action Section for Mobile */}
            <div className="sm:hidden">
              <Link 
                to={`/pick_stream/printers?mr_name=${itemIdentifierDetails.material_request}&item_code=${itemIdentifierDetails.item_code}&item_type=${itemIdentifierDetails.item_type}&id=${id}&qty=${itemIdentifierDetails.qty}`}
                className="block w-full text-center px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium"
              >
                <div className="flex items-center justify-center space-x-2">
                  <FaPrint size={16} />
                  <span>Print Identifier</span>
                </div>
              </Link>
            </div>
          </div>
        ) : (
          /* Empty State */
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="p-4 bg-gray-50 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
              <FaBarcode size={32} className="text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Data Available</h3>
            <p className="text-gray-500 mb-6">Unable to find details for this identifier.</p>
            <button 
              onClick={() => navigate('/pick_stream/tools/identifier-lookup')}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              type="button"
            >
              Back to Lookup
            </button>
          </div>
        )}

      </div>
    </main>
  );
}