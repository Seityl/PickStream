import { useState } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
} from 'react-router';
import { FaSpinner } from "react-icons/fa6";
import {getPrinterList} from '../../utils/api';
import {frappeClient} from '../../utils/client';
import { useAuth } from '../context/AuthContext';

function Printers() {
  const {user} = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const itemCode = searchParams.get('item_code');
  const itemType= searchParams.get('item_type');
  const materialRequest = searchParams.get('mr_name');
  
  const printers = useLoaderData();
  const navigate = useNavigate();

  async function sendPrintRequest(printer: string) {
    const params = {
      user: user,
      mr_name: materialRequest,
      item_code: itemCode,
      item_type: itemType,
      printer: printer
    };
    try {
      const response = await frappeClient.get('pick_stream.api.submit_print_request', params);
      navigate(-1);
    } catch(err) {
      console.error(err);
    }
  }

  return (
    <main>
      <header className='flex flex-row justify-center items-center px-4 py-6 bg-[#171717] text-white relative'>
        <p className='text-xl font-semibold'>Printers</p>
      </header>

      <div className='px-4 mt-10 flex flex-col gap-y-4'>
        {printers.length > 0 && printers.map((printer: string) => {
          return <button className='item-group-btn' onClick={() => sendPrintRequest(printer)}>{printer}</button>
        })}
      </div>
    </main>
  )
}

export default Printers;

export async function printersViewLoader() {
  return await getPrinterList();
}
