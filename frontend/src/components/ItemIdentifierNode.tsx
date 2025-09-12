import React from 'react';
import { AiFillProfile } from "react-icons/ai";
import { FaWarehouse, FaUser, FaArrowRight, FaClock } from "react-icons/fa";
import { Link } from 'react-router';

interface ItemIdentifierNodeProps {
  id: string;
  name: string;
  item_type: string;
  item_code: string;
  user: string;
  to_warehouse: string;
  from_warehouse?: string;
}

export default function ItemIdentifierNode(props: ItemIdentifierNodeProps) {
  const {
    name,
    item_type,
    item_code,
    to_warehouse,
    from_warehouse,
  } = props;

  return (
    <Link 
      to={`/pick_stream/tools/item-lookup/${encodeURIComponent(name)}`}
      className="block group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-xl"
      aria-label={`View details for ${name} - ${item_type} ${item_code}`}
    >
      <div 
        className="relative p-6 hover:bg-gray-50 transition-all duration-200 rounded-xl borderLeft: 4px solid blue-600;"
      >
        {/* Header Section */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0 p-2 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
              <AiFillProfile className="text-blue-600" size={20} />
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-gray-900 truncate text-lg">
                  {name}
                </h3>
                {item_code && (
                  <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700">
                    {item_code}
                  </span>
                )}
              </div>
              
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span className="inline-flex items-center space-x-1">
                  <span className="font-medium">Type:</span>
                  <span>{item_type}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Warehouse Transfer Section */}
        <div className="flex items-center justify-center mb-4 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-3 text-sm">
            <div className="flex items-center space-x-2 text-gray-700">
              <FaWarehouse className="text-gray-500" size={14} />
              <span className="font-medium">{from_warehouse}</span>
            </div>
            
            <FaArrowRight className="text-gray-400" size={12} />
            
            <div className="flex items-center space-x-2 text-gray-700">
              <FaWarehouse className="text-gray-500" size={14} />
              <span className="font-medium">{to_warehouse}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}