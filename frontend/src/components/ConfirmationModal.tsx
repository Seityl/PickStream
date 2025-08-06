import React from 'react';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ isOpen, onClose, onConfirm, title, message }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center" onClick={onClose}>
      <div className="bg-white p-6 rounded-lg shadow-lg z-50" onClick={e => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">{title}</h2>
        <p className="mb-6">{message}</p>
        <div className="flex justify-end gap-4">
          <button className="px-4 py-2 rounded text-gray-600 bg-gray-200 hover:bg-gray-300" onClick={onClose}>Cancel</button>
          <button className="px-4 py-2 rounded text-white bg-blue-500 hover:bg-blue-600" onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;