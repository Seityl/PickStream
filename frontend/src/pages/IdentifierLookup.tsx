import React from 'react';
import { useLoaderData, Link, LoaderFunctionArgs } from 'react-router';
import { FaArrowLeft, FaBarcode } from "react-icons/fa";
import { getCurrentUser } from '../../utils/auth';
import ItemIdentifierNode from '../components/ItemIdentifierNode';
import { getItemIdentifierList } from '../../utils/api';

// Type definitions
interface ItemIdentifier {
  id: string;
  barcode?: string;
  qrCode?: string;
  rfidTag?: string;
  itemName: string;
  description?: string;
  location?: string;
  timestamp: string;
  status: 'active' | 'inactive' | 'pending';
  // Add other properties as needed based on your ItemIdentifierNode props
}


function IdentifierLookup(): React.ReactElement {
  const itemIdentifiers = useLoaderData() as ItemIdentifier[];
  console.log(itemIdentifiers);

  return (
    <main>
      {/* Header Section - Consistent with home page style */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center space-x-4">
              <Link 
                to={`/pick_stream/tools`}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <FaArrowLeft size={20} className="text-gray-600" />
              </Link>
              <div className="flex items-center space-x-3">
                <div>
                  <h1 className="text-xl font-semibold text-gray-900">Identifier Lookup</h1>
                  <p className="text-sm text-gray-500">Search and manage item identifiers</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Section */}
      <div className="max-w-4xl mx-auto p-4">
        {/* Results Section */}
        <div className="space-y-4">
          {itemIdentifiers && itemIdentifiers.length > 0 ? (
            <>
              {/* Identifier List */}
              <div className="grid gap-4">
                {itemIdentifiers.map((itemIdentifier: ItemIdentifier, index: number) => (
                  <div 
                    key={index}
                    className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-200 transition-all duration-200"
                  >
                    <ItemIdentifierNode {...itemIdentifier} />
                  </div>
                ))}
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <div className="p-4 bg-gray-50 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                <FaBarcode size={32} className="text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Identifiers Found</h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                No item identifiers found. Check back later when you have scanned box or other items.
              </p>
              <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
                Refresh Data
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

export default IdentifierLookup;

export async function IdentifierLookupLoader({ }: LoaderFunctionArgs): Promise<ItemIdentifier[]> {
  const user: string | null = await getCurrentUser();
  
  if (!user) {
    throw new Error('User not authenticated');
    // Or handle the null case as appropriate for your app:
    // return [];
    // throw redirect('/login');
  }
  
  const crateTransitDetails: ItemIdentifier[] = await getItemIdentifierList(user);
  return crateTransitDetails;
}