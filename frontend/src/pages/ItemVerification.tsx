import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate,  } from 'react-router';
import { useSubmitVerification, useItemIdentifierDetails } from '../../utils/customApiHooks';
import { FaArrowLeft } from 'react-icons/fa';
import { toast } from 'react-toastify';
import { useAuth } from '../context/AuthContext';
import { frappeClient } from '../../utils/client';


function ItemVerification() {
  const { identifier_code } = useParams<{ identifier_code: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: itemDetailsResponse, error, isLoading } = useItemIdentifierDetails(identifier_code || '');
  const itemDetails = itemDetailsResponse?.data;
  const [quantity, setQuantity] = useState(0);

  useEffect(() => {
    if (itemDetails) {
      setQuantity(itemDetails.qty);
    }
  }, [itemDetails]);

  async function submitVerificationRequest() {
    try {
      const params = { user, identifier_code, items: JSON.stringify([{...itemDetails ,qty: quantity}]) };

      const response = await frappeClient.post('pick_stream.api.submit_verification_request', params);

      toast.success("Verification submitted successfully");
      navigate('/pick_stream/'); // Navigate to tools page after closing crate
    }
    catch(err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      } else {
        toast.error(err.message || "An error occurred");
      }
    }
  }

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center min-h-screen">Error loading item details</div>;
  }

  return (
    <main className='min-h-screen relative'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <Link to={`/pick_stream/verification`}>
          <FaArrowLeft size={24}/>
        </Link>
        <p className='mx-auto text-xl font-semibold'>{itemDetails?.item_code}</p>
      </header>

      <div className='px-4 mt-10'>
        {itemDetails ? (
          <>
            <p className='text-center mb-5'>From {itemDetails.from_warehouse} To {itemDetails.to_warehouse}</p>

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
                  <tr className="hover:bg-gray-50">
                    <td className="border border-gray-300 max-w-[150px] overflow-hidden text-ellipsis whitespace-nowrap px-4 py-2">
                      {itemDetails.item_code} {itemDetails.item_name}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">{itemDetails.uom}</td>
                    <td className="border border-gray-300 px-4 py-2">{quantity}</td>
                    <td className="border border-gray-300 px-4 py-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setQuantity(Math.max(0, quantity - 1))}
                          className="px-2 py-1 border border-gray-300 rounded hover:bg-gray-100"
                        >
                          −
                        </button>
                        <button
                          onClick={() => setQuantity(quantity + 1)}
                          className="px-2 py-1 border border-gray-300 rounded hover:bg-gray-100"
                        >
                          +
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
           <button className="modal-btn" onClick={() => submitVerificationRequest()}>Verify Item</button>
          </>
        ) : (
          <p className='text-center'>Item details not found.</p>
        )}
      </div>
    </main>
  );
}

export default ItemVerification;
