import React, { useState } from 'react';
import { X, Package, Tag, Scan } from 'lucide-react';

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

type CreateTransitModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onCreateTransit: (selectedItems: { crates: Crate[]; identifiers: Identifier[] }) => void;
  availableCrates: Crate[];
  availableIdentifiers: Identifier[];
};

function CreateTransitModal({
  isOpen,
  onClose,
  onCreateTransit,
  availableCrates,
  availableIdentifiers
}: CreateTransitModalProps) {
  // Removed mode state - only using scan mode now
  const [activeTab, setActiveTab] = useState<'crates' | 'identifiers'>('crates');
  const [selectedCrates, setSelectedCrates] = useState<Crate[]>([]);
  const [selectedIdentifiers, setSelectedIdentifiers] = useState<Identifier[]>([]);
  const [scanInput, setScanInput] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  const handleAddItem = () => {
    if (!scanInput.trim()) return;

    // Clear any previous error message
    setErrorMessage('');

    if (activeTab === 'crates') {
      const foundCrate = availableCrates.find(crate => 
        crate.crate_code.toLowerCase() === scanInput.toLowerCase()
      );
      if (foundCrate) {
        if (!selectedCrates.find(c => c.crate_code === foundCrate.crate_code)) {
          setSelectedCrates([...selectedCrates, foundCrate]);
          setScanInput('');
        } else {
          setErrorMessage(`Crate "${scanInput}" is already selected.`);
        }
      } else {
        setErrorMessage(`Crate "${scanInput}" not found in the available list.`);
      }
    } else {
      const foundIdentifier = availableIdentifiers.find(identifier => 
        identifier.identifier_code.toLowerCase() === scanInput.toLowerCase()
      );
      if (foundIdentifier) {
        if (!selectedIdentifiers.find(i => i.identifier_code === foundIdentifier.identifier_code)) {
          setSelectedIdentifiers([...selectedIdentifiers, foundIdentifier]);
          setScanInput('');
        } else {
          setErrorMessage(`Identifier "${scanInput}" is already selected.`);
        }
      } else {
        setErrorMessage(`Identifier "${scanInput}" not found in the available list.`);
      }
    }
  };

  const handleCheckboxChange = (item: Crate | Identifier, checked: boolean) => {
    const isCrate = 'crate_code' in item;
    
    if (isCrate) {
      const crate = item as Crate;
      if (checked) {
        if (!selectedCrates.find(c => c.crate_code === crate.crate_code)) {
          setSelectedCrates([...selectedCrates, crate]);
        }
      } else {
        setSelectedCrates(selectedCrates.filter(c => c.crate_code !== crate.crate_code));
      }
    } else {
      const identifier = item as Identifier;
      if (checked) {
        if (!selectedIdentifiers.find(i => i.identifier_code === identifier.identifier_code)) {
          setSelectedIdentifiers([...selectedIdentifiers, identifier]);
        }
      } else {
        setSelectedIdentifiers(selectedIdentifiers.filter(i => i.identifier_code !== identifier.identifier_code));
      }
    }
  };

  const handleCreateTransit = () => {
    onCreateTransit({ crates: selectedCrates, identifiers: selectedIdentifiers });
    // Reset state
    setSelectedCrates([]);
    setSelectedIdentifiers([]);
    setScanInput('');
    setErrorMessage('');
    // Reset to default state
    setActiveTab('crates');
  };

  const handleCancel = () => {
    // Reset state
    setSelectedCrates([]);
    setSelectedIdentifiers([]);
    setScanInput('');
    setErrorMessage('');
    setActiveTab('crates');
    onClose();
  };

  const currentAvailableItems = activeTab === 'crates' ? availableCrates : availableIdentifiers;
  const currentSelectedItems = activeTab === 'crates' ? selectedCrates : selectedIdentifiers;
  const hasSelectedItems = selectedCrates.length > 0 || selectedIdentifiers.length > 0;

  const isItemSelected = (item: Crate | Identifier) => {
    const isCrate = 'crate_code' in item;
    if (isCrate) {
      const crate = item as Crate;
      return selectedCrates.some(c => c.crate_code === crate.crate_code);
    } else {
      const identifier = item as Identifier;
      return selectedIdentifiers.some(i => i.identifier_code === identifier.identifier_code);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Create Transit</h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Scan Mode Header */}
          <div className="flex items-center gap-2 mb-2">
            <Scan size={18} />
            <h3 className="font-medium text-gray-900">Scan or Select Items</h3>
          </div>

          {/* Scan Input Section */}
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-600 mb-3">Enter Code</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={scanInput}
                  onChange={(e) => {
                    setScanInput(e.target.value);
                    if (errorMessage) setErrorMessage(''); // Clear error when user starts typing
                  }}
                  placeholder="Scan or type crate/identifier code"
                  className={`flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent ${
                    errorMessage 
                      ? 'border-red-300 focus:ring-red-500' 
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddItem()}
                />
                <button
                  onClick={handleAddItem}
                  className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Add
                </button>
              </div>
              {errorMessage && (
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{errorMessage}</p>
                </div>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('crates')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'crates'
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Package size={16} />
              Crates ({availableCrates.length})
            </button>
            <button
              onClick={() => setActiveTab('identifiers')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'identifiers'
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Tag size={16} />
              Identifiers ({availableIdentifiers.length})
            </button>
          </div>

          {/* Available Items List */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {activeTab === 'crates' ? <Package size={18} /> : <Tag size={18} />}
              <h3 className="font-medium text-gray-900">
                Available {activeTab === 'crates' ? 'Crates' : 'Identifiers'}
              </h3>
              <span className="text-sm text-gray-500">
                ({currentSelectedItems.length} selected)
              </span>
            </div>

            {/* Table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full min-w-[600px]">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                          Select
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                          Code
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                          From
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                          To
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {currentAvailableItems.length > 0 ? (
                        currentAvailableItems.map((item) => {
                          const isCrate = 'crate_code' in item;
                          const code = isCrate ? item.crate_code : item.identifier_code;
                          const isSelected = isItemSelected(item);
                          
                          return (
                            <tr key={code} className="hover:bg-gray-50 transition-colors">
                              <td className="px-4 py-3 w-16">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={(e) => handleCheckboxChange(item, e.target.checked)}
                                  className="w-4 h-4 text-gray-800 border-gray-300 rounded focus:ring-gray-500"
                                />
                              </td>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900 w-32">
                                <div className="truncate" title={code}>{code}</div>
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600 w-40">
                                <div className="truncate" title={item.source_warehouse}>{item.source_warehouse}</div>
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-600 w-40">
                                <div className="truncate" title={item.target_warehouse}>{item.target_warehouse}</div>
                              </td>
                              <td className="px-4 py-3 text-sm w-24">
                                {isSelected ? (
                                  <span className="text-green-600 font-medium">Selected</span>
                                ) : (
                                  <span className="text-gray-400">Available</span>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-gray-500 text-sm">
                            No {activeTab} available
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-4 border-t border-gray-200">
          <button
            onClick={handleCancel}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreateTransit}
            disabled={!hasSelectedItems}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              hasSelectedItems
                ? 'bg-gray-800 text-white hover:bg-gray-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Create Transit ({selectedCrates.length + selectedIdentifiers.length} items)
          </button>
        </div>
      </div>
    </div>
  );
}

export default CreateTransitModal;