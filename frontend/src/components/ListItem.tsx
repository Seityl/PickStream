import React from 'react';
import { FaBox, FaTag, FaChevronRight } from 'react-icons/fa';

type ListItemProps = {
  code: string;
  type: 'crate' | 'item';
  onClick?: () => void;
  children?: React.ReactNode;
  showChevron?: boolean;
};

const ListItem: React.FC<ListItemProps> = ({ 
  code, 
  type, 
  onClick, 
  children, 
  showChevron = true
}) => {
  const isCrate = type === 'crate';

  const content = (
    <div className="w-full flex items-center p-3 hover:bg-gray-25 transition-colors rounded-lg group">
      {/* Left side - Icon */}
      <div className="flex items-center mr-4">
        <div className={`p-2 rounded-lg ${
          isCrate 
            ? 'bg-blue-50 border border-blue-100' 
            : 'bg-green-50 border border-green-100'
        }`}>
          {isCrate ? (
            <FaBox className="text-blue-600" size={16} />
          ) : (
            <FaTag className="text-green-600" size={16} />
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="font-mono text-gray-900 font-medium text-base">
            {code}
          </span>
          
          {/* Type badge */}
          <span className={`px-2 py-1 text-xs font-medium rounded-md ${
            isCrate
              ? 'bg-blue-100 text-blue-800'
              : 'bg-green-100 text-green-800'
          }`}>
            {isCrate ? 'Crate' : 'Item'}
          </span>
        </div>
      </div>

      {/* Right side - Chevron */}
      {showChevron && (
        <div className="ml-4 opacity-40 group-hover:opacity-60 transition-opacity">
          <FaChevronRight className="text-gray-500" size={14} />
        </div>
      )}
    </div>
  );

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className="w-full text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
        aria-label={`${isCrate ? 'Crate' : 'Item'} ${code}`}
      >
        {content}
      </button>
    );
  }

  return <div className="w-full">{children || content}</div>;
};

export default ListItem;