import { useState } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
} from 'react-router';
import { FaSpinner } from "react-icons/fa6";
import {getPrinterList} from '../../utils/api';
import {frappeClient} from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';

function Printers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const itemCode = searchParams.get('item_code');
  const itemType= searchParams.get('item_type');
  const materialRequest = searchParams.get('mr_name');
  const quantity = searchParams.get('qty');
  const identifier = searchParams.get('id');
  const [hidden, setHidden] = useState(true);
  const [printer, setPrinter] = useState('');
  const [numOfCopies, setNumOfCopies] = useState(quantity && typeof parseInt(quantity) === "number" ? parseInt(quantity) : 0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const printers = useLoaderData();
  const navigate = useNavigate();

  function openPrintModal(printer: string) {
    setPrinter(printer);
    setHidden(false);
  }
  function closePrintModal() {
    setHidden(true);
  }
  async function sendPrintRequest(printer: string, qty: number ) {
    const user = await getCurrentUser();
    const params: any = {
      mr_name: materialRequest,
      printer: printer,
      user: user,
      item_code: itemCode,
      item_type: itemType,
      qty: qty,
    };

    if (identifier) {
      params['identifier'] = identifier;
    }
    try {
      setIsLoading(true);
      const response = await frappeClient.get('pick_stream.api.submit_print_request', params);
      closePrintModal()
      navigate(-1);
    } catch(err:any) {
      setError(err.message.error.error_message);
      toast(err.message.error.error_message, {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
        //transition={Bounce}
      })
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main>
      <header className='flex flex-row justify-center items-center px-4 py-6 bg-[#171717] text-white relative'>
        <p className='text-xl font-semibold'>Printers</p>
      </header>

      <div className='px-4 mt-10 flex flex-col gap-y-4'>
      {!hidden ? 
        <>
            <div className="modal-backdrop min-h-screen" onClick={closePrintModal}></div>

            <div className="modal">
              <div className="flex flex-col items-center modal-content">
                  <p className=''>Number of Copies</p>

                  <div className="input-container w-full">
                      <input
                        className="input-field mb-0 w-full"
                        name="num_of_copies"
                        id="num_of_copies"
                        type="number"
                        placeholder="Enter Number"
                        value={numOfCopies}
                        onChange={(e) => {setNumOfCopies(parseInt(e.target.value));}}
                      />
                  </div>

                  <button className="modal-btn" type="submit" onClick={() => sendPrintRequest(printer, numOfCopies)}>
                  {error ? error : !isLoading ? 'Print Labels' : 'Printing...'}
                  </button>
                </div>
              </div>
          </>
            :  
          ''
        } 
        {printers.length > 0 && printers.map((printer: string) => {
          return <button className='item-group-btn' onClick={() => openPrintModal(printer)}>{printer}</button>
        })}
      </div>
    </main>
  )
}

export default Printers;

export async function printersViewLoader() {
  return await getPrinterList();
}
