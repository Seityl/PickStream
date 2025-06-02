import {useState, useEffect} from 'react';
import { useSearchParams, useParams, Link, LoaderFunctionArgs, useLoaderData,  } from 'react-router';
import { useAuth } from '../context/AuthContext';
import {frappeClient} from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import { FaArrowLeft } from "react-icons/fa";
import {getUserCrateItemDetails } from '../../utils/api';
import { toast

 } from 'react-toastify';
type MaterialRequest = {
  name: string;
  source_warehouse: string | null;
  target_warehouse: string;
  status: string;
  item_group_availability: []
};

function Crate() {
  const crateDetails = useLoaderData();
  const [items, setItems] = useState<any[]>(crateDetails && crateDetails.items || []); 
  const [materialRequestData, setMaterialRequestData] = useState<MaterialRequest | null>(null);
  
  async function closeCrate() {
    try {
      const params = {crate_code: crateDetails.crate_code, /*user: await getCurrentUser()*/};

      const response = await frappeClient.get('pick_stream.api.submit_close_crate_request', params);
      console.log(response.data.message);
    }
    catch(err: any) {
      if (err.httpStatus === 404) {
        toast.error("Something went wrong. Please try again.");
      }
    }
  }
  // useEffect(() => {
  //   const data = {user: user, mr_name: materialRequestName};

  //   const fetchMaterialRequestDetails = async function () {
  //     const response = await frappeClient.get('pick_stream.api.get_material_request_detail_view', data);
    
  //     setMaterialRequestData(response.message.data);
  //   };

  //   fetchMaterialRequestDetails();
  // }, []);
  return (
    <main className='min-h-screen'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <Link to={`/pick_stream/material-requests`}>
          <FaArrowLeft size={24}/>
        </Link>

        <p className='mx-auto text-xl font-semibold'>{crateDetails && crateDetails.crate_code}</p>
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
        {/* <div className="w-[280px] overflow-x-auto mb-20">
          <table className="demo">
            {crateDetails.items.map((item: any) => (
              <tr key={item.name}>
                <td>{item.item_code} {item.item_name}</td>
                <td>{item.uom}</td>
                <td>{item.qty}</td>
                <td>+ -</td>
              </tr>
            ))}
          </table>
        </div> */}
          
         <button className="modal-btn" onClick={() => closeCrate()}>Confirm and Close</button>
          </>
        )
        : <p className='text-center'>You currently have no active crates</p>}
      </div>
    </main>
  );
}

export default Crate;

export async function CrateLoader({params}: LoaderFunctionArgs) {
  const crateDetails = await getUserCrateItemDetails();
  return crateDetails;
}
