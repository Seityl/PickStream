import { Link } from 'react-router';
import { FaBoxOpen, FaBarcode, FaSearch, FaClipboardList, FaBox } from "react-icons/fa";
import { MdInventory } from "react-icons/md";

export default function Tool() {
  const toolItems = [
    { 
      path: '/pick_stream/tools/identifier-lookup',
      label: 'Identifier Lookup',
      icon: FaSearch,
      description: 'Search and manage item identifiers'
    },
    { 
      path: '/pick_stream/tools/active-crate', 
      label: 'Active Crate', 
      icon: FaBoxOpen,
      description: 'Manage and track active crate'
    },
    { 
      path: '/pick_stream/tools/crate-check', 
      label: 'Crate Check', 
      icon: FaBox,
      description: 'Scan and check crate details'
    },
    { 
      path: '/pick_stream/tools/barcode-scanner', 
      label: 'Barcode Scanner', 
      icon: FaBarcode,
      description: 'Scan barcodes for quick identification'
    },
    { 
      path: '/pick_stream/tools/inventory-check', 
      label: 'Inventory Check', 
      icon: MdInventory,
      description: 'Quick inventory level verification'
    },
    { 
      path: '/pick_stream/tools/audit-log', 
      label: 'Audit Log', 
      icon: FaClipboardList,
      description: 'View recent activity'
    }
  ];

  return (
    <main className="p-4 max-w-6xl mx-auto">
      {/* Header Section */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Tools & Utilities</h1>
        <p className="text-gray-600">Quick access tools to support your workflow</p>
      </div>

      {/* Tools Grid */}
      <div className="mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {toolItems.map(({ path, label, icon: Icon, description }) => (
            <Link
              key={path}
              to={path}
              className="group block p-4 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:border-blue-200 transition-all duration-200 active:scale-[0.98]"
            >
              <div className="flex items-center space-x-3 mb-3">
                <div className="p-2 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
                  <Icon size={20} className="text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                  {label}
                </h3>
              </div>
              <p className="text-gray-500 text-sm mb-3 leading-relaxed">{description}</p>
              
              <div className="flex items-center text-blue-600 text-xs font-medium group-hover:text-blue-700">
                Open Tool
                <svg className="ml-1 w-3 h-3 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}