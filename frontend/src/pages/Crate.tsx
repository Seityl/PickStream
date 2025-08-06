import { useState, useEffect } from 'react';
import { Link, useNavigate, useLoaderData } from 'react-router';
import { FaArrowLeft } from 'react-icons/fa';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import { useCloseCrate } from '../../utils/customApiHooks';
import { getUserCrateItemDetails } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

export async function crateLoader() {
  const user = await getCurrentUser();
  if (!user) {
    return null;
  }
  return await getUserCrateItemDetails();
}

function Crate() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const crateDetails = useLoaderData();
  const [items, setItems] = useState<any[]>([]);

  // Update items state when crateDetails changes
  useEffect(() => {
    if (crateDetails?.items) {
      setItems(crateDetails.items);
    } else {
      setItems([]);
    }
  }, [crateDetails]);

  const closeCrateMutation = useCloseCrate();

  async function closeCrate() {
    closeCrateMutation.mutate(
      {
        crate_code: crateDetails.crate_code,
        // items: items.map(item => ({ ...item, qty: item.scanned_qty })),
      },
      {
        onSuccess: () => {
          toast.success('Crate closed successfully');
          navigate('/pick_stream/tools');
        },
        onError: (err) => {
          console.error(err);
          toast.error('Failed to close crate');
        },
      }
    );
  }



  if (!crateDetails || items.length === 0) {
    return (
      <main className="min-h-screen flex flex-col">
        <header className="flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative">
          <Link to="/pick_stream/tools">
            <FaArrowLeft size={24} />
          </Link>
          <p className="mx-auto text-xl font-semibold">Crate</p>
        </header>
        <div className="flex-grow flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-semibold">You currently have no active crates.</p>
            <p className="text-sm text-gray-500">Go to a material request to start picking.</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative">
        <Link to="/pick_stream/tools">
          <FaArrowLeft size={24} />
        </Link>
        <p className="mx-auto text-xl font-semibold">{crateDetails?.crate_code}</p>
      </header>
      <div className="px-4 mt-10">
        <p className="text-center mb-5">
          From {crateDetails.from_warehouse} To {crateDetails.to_warehouse}
        </p>
        <p className="mb-5">Items</p>
        <div className="w-full overflow-x-auto mb-20">
          <table className="min-w-full table-auto border border-gray-300 border-collapse">
            <thead className="bg-gray-200">
              <tr>
                <th className="border border-gray-300 px-4 py-2 text-left">Item</th>
                <th className="border border-gray-300 px-4 py-2 text-left">UOM</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Qty</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={item.name} className="hover:bg-gray-50">
                  <td className="border border-gray-300 max-w-[150px] overflow-hidden text-ellipsis whitespace-nowrap px-4 py-2">
                    {item.item_code} {item.item_name}
                  </td>
                  <td className="border border-gray-300 px-4 py-2">{item.uom}</td>
                  <td className="border border-gray-300 px-4 py-2">{item.scanned_qty}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          const newItems = [...items];
                          newItems[index].scanned_qty = Math.max(0, newItems[index].scanned_qty - 1);
                          setItems(newItems);
                        }}
                        className="px-2 py-1 border border-gray-300 rounded hover:bg-gray-100"
                      >
                        −
                      </button>
                      <button
                        onClick={() => {
                          const newItems = [...items];
                          newItems[index].scanned_qty += 1;
                          setItems(newItems);
                        }}
                        className="px-2 py-1 border border-gray-300 rounded hover:bg-gray-100"
                      >
                        +
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button className="modal-btn" onClick={closeCrate}>
          Confirm and Close
        </button>
      </div>
    </main>
  );
}

export default Crate;
