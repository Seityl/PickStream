import React from 'react';
import { AiFillProfile } from "react-icons/ai";
import { FaArrowRight, FaCheckCircle, FaExclamationCircle, FaClock } from "react-icons/fa";
import { Link } from 'react-router';
import { MatReqItem } from '../../types';

// Use the actual type from your data structure
type ItemGroupAvailability = Record<string, any> & {
  name?: string;
  available?: boolean;
};

export default function MaterialRequestItem(props: MatReqItem) {
  const { name, target_warehouse, source_warehouse, status, item_group_availability } = props;

  // Enhanced status configuration with icons and colors
  const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; textColor: string }> = {
    Open: {
      color: '#10B981', // Green-500
      bgColor: '#D1FAE5', // Green-100
      textColor: '#065F46', // Green-800
      icon: <FaCheckCircle className="w-3 h-3" />
    },
    Pending: {
      color: '#F59E0B', // Amber-500
      bgColor: '#FEF3C7', // Amber-100
      textColor: '#92400E', // Amber-800
      icon: <FaClock className="w-3 h-3" />
    },
    'In Progress': {
      color: '#3B82F6', // Blue-500
      bgColor: '#DBEAFE', // Blue-100
      textColor: '#1E40AF', // Blue-800
      icon: <FaClock className="w-3 h-3" />
    },
    Blocked: {
      color: '#EF4444', // Red-500
      bgColor: '#FEE2E2', // Red-100
      textColor: '#991B1B', // Red-800
      icon: <FaExclamationCircle className="w-3 h-3" />
    }
  };

  const currentStatus = statusConfig[status] || statusConfig['Open'];

  // Calculate availability summary with proper type checking
  const availableCount = item_group_availability.filter((item: ItemGroupAvailability) => item.available === true).length;
  const totalCount = item_group_availability.length;
  const hasUnavailableItems = availableCount < totalCount;

  return (
    <Link 
      to={`/pick_stream/material-requests/${name}`}
      className="block transition-all duration-200 hover:translate-y-[-1px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:ring-offset-2 rounded-xl"
    >
      <div 
        className="relative p-4 bg-white border-l-4 hover:shadow-md transition-shadow duration-200"
        style={{ borderLeftColor: currentStatus.color }}
      >
        {/* Header Section */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-3 min-w-0 flex-1">
            <div className="flex-shrink-0 p-2 bg-gray-50 rounded-lg">
              <AiFillProfile className="w-5 h-5 text-gray-600" />
            </div>
            
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-gray-900 truncate text-base">
                {name}
              </h3>
              <div className="flex items-center mt-1">
                <span 
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                  style={{ 
                    backgroundColor: currentStatus.bgColor, 
                    color: currentStatus.textColor 
                  }}
                >
                  {currentStatus.icon}
                  <span className="ml-1">{status}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Availability Summary Badge */}
          <div className={`flex-shrink-0 ml-3 px-2.5 py-1 rounded-full text-xs font-medium ${
            hasUnavailableItems 
              ? 'bg-red-100 text-red-800' 
              : 'bg-green-100 text-green-800'
          }`}>
            {availableCount}/{totalCount} Available
          </div>
        </div>

        {/* Warehouse Route Section */}
        <div className="flex items-center text-sm text-gray-600 mb-3 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2 min-w-0 flex-1">
            <span className="font-medium truncate">
              {source_warehouse || 'KG Warehouse - JP'}
            </span>
            <FaArrowRight className="flex-shrink-0 w-3 h-3 text-gray-400" />
            <span className="font-medium truncate">
              {target_warehouse}
            </span>
          </div>
        </div>

        {/* Item Groups Section */}
        {item_group_availability.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Item Groups ({item_group_availability.length})
            </h4>
            
            {/* Show first 3 items, with expandable option for more */}
            <div className="space-y-1.5">
              {item_group_availability.slice(0, 3).map((item_group: ItemGroupAvailability, index: number) => (
                <div 
                  key={index}
                  className={`flex items-center space-x-2 p-2.5 rounded-lg text-sm transition-colors ${
                    item_group.available 
                      ? 'bg-green-50 border border-green-200' 
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  {item_group.available ? (
                    <FaCheckCircle className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
                  ) : (
                    <FaExclamationCircle className="w-3.5 h-3.5 text-red-600 flex-shrink-0" />
                  )}
                  <span className={`font-medium truncate ${
                    item_group.available ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {item_group.name || 'Unknown Item'}
                  </span>
                </div>
              ))}
              
              {/* Show remaining count if more than 3 items */}
              {item_group_availability.length > 3 && (
                <div className="text-xs text-gray-500 px-2 py-1 text-center bg-gray-50 rounded-lg">
                  +{item_group_availability.length - 3} more item groups
                </div>
              )}
            </div>
          </div>
        )}

        {/* Hover indicator */}
        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <div className="w-2 h-2 rounded-full bg-blue-500"></div>
        </div>
      </div>
    </Link>
  );
}