import {useFrappeGetCall, useFrappeAuth,} from 'frappe-react-sdk';
import {useParams, useNavigate, redirect, Link} from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';

export default function ItemIdentifierDetail() {
  const navigate = useNavigate();
  const {currentUser} = useFrappeAuth();
  const {id} = useParams();
  const { data: response } = useFrappeGetCall<{ message: any }>(
    "pick_stream.api.get_item_identifier_details",
    {
      item_identifier: id
    },
    undefined,
    {
      revalidateOnFocus: true
    },
    "GET"
  );

  const itemIdentifierDetails= response?.message.data;
  console.log(itemIdentifierDetails)

  return (
    <main className="relative min-h-[calc(100vh+70px)] w-full flex flex-col">
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() =>navigate('/pick_stream/tools/identifier-lookup')}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{id}</p>
      </header>

      <div className="px-4 mt-10">
      { itemIdentifierDetails && (
      <> 
      <div className='flex flex-col gap-y-3.5'>
        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">📦 Item Details</h2>
          <div className="space-y-1 text-gray-700">
            <p><span className="font-medium">Item Code:</span> {itemIdentifierDetails.item_code}</p>
            <p><span className="font-medium">Item Type:</span> {itemIdentifierDetails.item_type}</p>
            <p><span className="font-medium">UOM:</span> {itemIdentifierDetails.uom}</p>
          </div>
        </div>

        <hr/>
        
        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">📋 Material Request</h2>
          <p className="text-gray-700"><span className="font-medium">Request No:</span>  {itemIdentifierDetails.material_request}</p>
        </div>

        <hr/>

        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">🏬 Transfer Details</h2>
          <div className="space-y-1 text-gray-700">
            <p><span className="font-medium">From:</span> {itemIdentifierDetails.from_warehouse}</p>
            <p><span className="font-medium">To:</span> {itemIdentifierDetails.to_warehouse}</p>
          </div>
        </div>

        <hr/>

        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">🕒 Timestamps</h2>
          <div className="space-y-1 text-gray-700">
            <p><span className="font-medium">Date Created:</span> {itemIdentifierDetails.date_created}</p>
            <p><span className="font-medium">Printed:</span> {itemIdentifierDetails.printed}</p>
            <p><span className="font-medium">Date Printed:</span> {itemIdentifierDetails.date_printed || 'N/A'}</p>
          </div>
        </div>

        <Link to={`/pick_stream/printers?mr_name=${itemIdentifierDetails.material_request}&item_code=${itemIdentifierDetails.item_code}&item_type=${itemIdentifierDetails.item_type}&id=${id}&qty=${itemIdentifierDetails.qty}`} className="mt-4 inline-block bg-black text-white text-center font-bold px-4 py-2 rounded hover:bg-black">Print Identifier</Link>
        
      </div>
      </>
      )}
      </div>
    </main>
  )
}
