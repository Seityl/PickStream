import { useState, useEffect } from 'react';
import { useParams, Link, useLoaderData, LoaderFunctionArgs } from 'react-router';
import { getCrateDetails } from '../../utils/api';
import { frappeClient } from '../../utils/client';
import { FaArrowLeft } from "react-icons/fa";
import { toast } from 'react-toastify';

export async function crateReceivingLoader({ params }: LoaderFunctionArgs) {
  const { crateId } = params;
  if (!crateId) {
    throw new Response("Crate ID not found", { status: 404 });
  }
  const crateDetails = await getCrateDetails(crateId);
  return { crateDetails };
}

function CrateReceiving() {
  const { crateDetails } = useLoaderData() as { crateDetails: any };
  const [items, setItems] = useState<any[]>([]); // Initialize as empty array
  
  // Update items when crateDetails becomes available
  useEffect(() => {
    if (crateDetails?.items) {
      setItems(crateDetails.items);
    }
  }, [crateDetails]);
  
  async function closeCrate() {
    try {
      const params = { crate_code: crateDetails.crate_code };

      const response = await frappeClient.get('pick_stream.api.submit_close_crate_request', params);
      console.log(response.data.message);
      toast.success("Crate closed successfully");
    }
    catch(err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    }
  }
  
  return (
    <main className='min-h-screen'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <Link to={`/pick_stream/receiving`}>
          <FaArrowLeft size={24}/>
        </Link>

        <p className='mx-auto text-xl font-semibold'>{crateDetails?.crate_code}</p>
      </header>
      <div className='px-4 mt-10'>
        {crateDetails && crateDetails.items?.length > 0 ? (
          <>
          <p className='text-center mb-5'>From {crateDetails.from_warehouse} To {crateDetails.to_warehouse}</p>

        <p className='mb-5'>Items</p>
        
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
                <tr key={item.item_code} className="hover:bg-gray-50">
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
          
        <button className="modal-btn" onClick={() => closeCrate()}>Verify Crate</button>
          </>
        )
        : <p className='text-center'>You currently have no active crates</p>}
      </div>
    </main>
  );
}

export default CrateReceiving;
