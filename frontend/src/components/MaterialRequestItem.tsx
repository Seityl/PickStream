import React from 'react';
import { AiFillProfile } from "react-icons/ai";
import { FaArrowRight, FaCheckCircle, FaCircle } from "react-icons/fa";
import { Link } from 'react-router';
import { MatReqItem, ItemGroupDisplay, AvailabilityStatus } from '../../types';

export default function MaterialRequestItem(props: MatReqItem) {
  const { name, target_warehouse, source_warehouse, status, item_group_availability } = props;

  const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; textColor: string }> = {
    Open: {
      color: '#10B981', // Green-500
      bgColor: '#D1FAE5', // Green-100
      textColor: '#065F46', // Green-800
      icon: <FaCheckCircle className="w-3 h-3" />
    }
  };

  const currentStatus = statusConfig[status];

  // Map availability status to human-readable reason
  const getReasonText = (availabilityStatus: AvailabilityStatus): string | undefined => {
    switch (availabilityStatus) {
      case 'already_picked':
        return 'Already Picked';
      case 'no_stock':
        return 'No Stock';
      case 'available':
      default:
        return undefined;
    }
  };

  // Transform object to array format for rendering
  // item_group_availability is now { "Group Name": "available" | "already_picked" | "no_stock" }
  const itemGroupsArray: ItemGroupDisplay[] = React.useMemo(() => {
    if (!item_group_availability || typeof item_group_availability !== 'object') {
      return [];
    }

    return Object.entries(item_group_availability).map(([itemGroupName, availabilityStatus]) => ({
      name: itemGroupName,
      status: availabilityStatus as AvailabilityStatus,
      available: availabilityStatus === 'available',
      reason: getReasonText(availabilityStatus as AvailabilityStatus)
    }));
  }, [item_group_availability]);

  // Separate available and unavailable item groups
  const availableItemGroups = itemGroupsArray.filter(item => item.available);
  const unavailableItemGroups = itemGroupsArray.filter(item => !item.available);
  const totalPicksNeeded = availableItemGroups.length;
  const shouldShowUnavailable = availableItemGroups.length <= 3;

  return (
    <Link 
      to={`/pick_stream/material-requests/${name}`}
      className="block transition-all duration-200 hover:translate-y-[-1px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:ring-offset-2 rounded-xl"
    >
      <div 
        className="relative p-4 bg-white hover:shadow-md transition-shadow duration-200"
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
            </div>
          </div>

          {/* Picks Needed Badge */}
          {totalPicksNeeded > 0 && (
            <div className="flex-shrink-0 ml-3 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {totalPicksNeeded} Pick {totalPicksNeeded === 1 ? 'List' : 'Lists'}
            </div>
          )}
        </div>

        {/* Warehouse Route Section */}
        <div className="flex items-center text-sm text-gray-600 mb-3 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2 min-w-0 flex-1">
            <span className="font-medium truncate">
              {source_warehouse}
            </span>
            <FaArrowRight className="flex-shrink-0 w-3 h-3 text-gray-400" />
            <span className="font-medium truncate">
              {target_warehouse}
            </span>
          </div>
        </div>

        {/* Item Groups Section */}
        {(availableItemGroups.length > 0 || unavailableItemGroups.length > 0) && (
          <div className="space-y-2">
            {/* Show first 3 available pick lists */}
            {availableItemGroups.length > 0 && (
              <div className="space-y-1.5">
                {availableItemGroups.slice(0, 3).map((item_group, index) => (
                  <div 
                    key={`available-${index}`}
                    className="flex items-center space-x-2 p-2.5 rounded-lg text-sm transition-colors bg-blue-50 border border-blue-200"
                  >
                    <FaCircle className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                    <span className="font-medium truncate text-blue-800">
                      {item_group.name}
                    </span>
                    
                    {/* Status indicator */}
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium ml-auto flex-shrink-0 bg-blue-100 text-blue-700">
                      To Pick
                    </span>
                  </div>
                ))}
                
                {/* Show remaining count if more than 3 available items */}
                {availableItemGroups.length > 3 && (
                  <div className="text-xs text-gray-500 px-2 py-1 text-center bg-gray-50 rounded-lg">
                    +{availableItemGroups.length - 3} more pick {availableItemGroups.length - 3 === 1 ? 'list' : 'lists'}
                  </div>
                )}
              </div>
            )}

            {/* Show unavailable item groups only if there are 3 or fewer available pick lists */}
            {shouldShowUnavailable && unavailableItemGroups.length > 0 && (
              <div className="space-y-1.5 mt-2">
                {unavailableItemGroups.map((item_group, index) => (
                  <div 
                    key={`unavailable-${index}`}
                    className="flex items-center space-x-2 p-2.5 rounded-lg text-sm bg-gray-50 border border-gray-200 opacity-70"
                  >
                    <FaCircle className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                    <span className="font-medium truncate text-gray-700">
                      {item_group.name}
                    </span>
                    
                    {/* Reason badge with specific text based on status */}
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium ml-auto flex-shrink-0 bg-gray-100 text-gray-700">
                      {item_group.reason || 'Unavailable'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Show message if no item groups at all */}
        {itemGroupsArray.length === 0 && (
          <div className="text-sm text-gray-500 text-center py-2 bg-gray-50 rounded-lg">
            No item groups assigned
          </div>
        )}
      </div>
    </Link>
  );
}