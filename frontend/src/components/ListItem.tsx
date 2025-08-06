import React from 'react';

type ListItemProps = {
  code: string;
  type: 'crate' | 'item';
  onClick?: () => void;
  children?: React.ReactNode;
};

const ListItem: React.FC<ListItemProps> = ({ code, type, onClick, children }) => {
  const content = (
    <div className="w-full bg-gray-800 p-4 rounded-lg flex justify-between items-center cursor-pointer">
      <span className="text-white font-semibold">{code}</span>
      <span className="text-sm font-semibold text-gray-400">{type === 'crate' ? 'Crate' : 'Item'}</span>
    </div>
  );

  if (onClick) {
    return <div onClick={onClick}>{content}</div>;
  }

  return <>{children || content}</>;
};

export default ListItem;