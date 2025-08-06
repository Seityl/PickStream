import { useState } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
} from 'react-router';
import { FaSpinner } from "react-icons/fa6";
import { getPrinterList } from '../../utils/api';
import { frappeClient } from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';

// Define interface for print request parameters
interface PrintRequestParams {
  mr_name: string | null;
  printer: string;
  user: string;
  item_code: string | null;
  item_type: string | null;
  qty: number;
  identifier?: string | null; // Make identifier optional with proper typing
}

function Printers() {
  const [searchParams] = useSearchParams();
  const itemCode = searchParams.get('item_code');
  const itemType = searchParams.get('item_type');
  const materialRequest = searchParams.get('mr_name');
  const quantity = searchParams.get('qty');
  const identifier = searchParams.get('id');
  const [hidden, setHidden] = useState(true);
  const [printer, setPrinter] = useState<string>(''); // Add type annotation
  const [numOfCopies, setNumOfCopies] = useState<number>(
    quantity && !isNaN(parseInt(quantity)) ? parseInt(quantity) : 0
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const printers = useLoaderData() as string[]; // Add type assertion
  const navigate = useNavigate();

  function openPrintModal(printerName: string) { // Add type annotation
    setPrinter(printerName);
    setHidden(false);
    setError(''); // Clear any previous errors
  }

  function closePrintModal() {
    setHidden(true);
    setError('');
  }

  async function sendPrintRequest(printerName: string, qty: number) { // Add type annotations
    // Validate input
    if (qty <= 0) {
      setError('Number of copies must be greater than zero');
      return;
    }

    try {
      setIsLoading(true);
      setError('');
      
      const user = await getCurrentUser();
      
      // Add null check
      if (!user) {
        setError('User not authenticated');
        return;
      }
      
      const params: PrintRequestParams = {
        mr_name: materialRequest,
        printer: printerName,
        user: user,  // Now TypeScript knows user is not null
        item_code: itemCode,
        item_type: itemType,
        qty: qty,
      };

      if (identifier) {
        params.identifier = identifier;
      }
      
      const response = await frappeClient.get('pick_stream.api.submit_print_request', params);
      toast.success('Print request submitted successfully', {
        position: "bottom-right",
        autoClose: 3000,
      });
      closePrintModal();
      navigate(-1);
    } catch(err: any) { // Add type annotation for error
      const errorMessage = err?.message?.error?.error_message || 
                          err?.message || 
                          'Failed to submit print request';
      
      setError(errorMessage);
      toast.error(errorMessage, {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
      });
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
        {!hidden && (
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
                    onChange={(e) => setNumOfCopies(parseInt(e.target.value) || 0)}
                  />
                </div>

                <button 
                  className="modal-btn" 
                  type="submit" 
                  onClick={() => sendPrintRequest(printer, numOfCopies)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center">
                      <FaSpinner className="animate-spin mr-2" />
                      Printing...
                    </span>
                  ) : (
                    'Print Labels'
                  )}
                </button>
                {error && <p className="text-red-500 mt-2">{error}</p>}
              </div>
            </div>
          </>
        )}
        
        {printers.length === 0 ? (
          <div className="text-center py-5">
            No printers available.
          </div>
        ) : (
          printers.map((printer) => (
            <button 
              key={printer} 
              className='item-group-btn' 
              onClick={() => openPrintModal(printer)}
            >
              {printer}
            </button>
          ))
        )}
      </div>
    </main>
  );
}

export default Printers;

export async function printersViewLoader() {
  return await getPrinterList();
}
