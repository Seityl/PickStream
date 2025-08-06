import { useState, useEffect, useCallback } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
  LoaderFunctionArgs, 
  useLocation,
  redirect
} from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';
import { getPickingViewItem } from '../../utils/api';
import { frappeClient } from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import SkipItemModal from '../components/SkipItemModal';
import ScanItemModal from '../components/ScanItemModal';
import ScanAsBoxModal from '../components/ScanAsBoxModal';
import ScanAsOtherModal from '../components/ScanAsOtherModal';
import { toast } from 'react-toastify';

// Define proper types
type SourceItem = {
  item_code: string;
  description: string;
  requested_qty: string;
  uom: string;
  from_warehouse: string;
  to_warehouse: string;
  idx: number;
  item_count: number;
  crate_code?: string;
};

type SubmitScanOptions = {
  scannedQuantity: number;
  itemType: string;
  crates?: Array<{ scanned_qty: number; crate_code: string; uom: string }>;
  closeCrate?: boolean;
};

// Standard toast configuration
const TOAST_CONFIG = {
  position: "bottom-right" as const,
  autoClose: 5000,
  hideProgressBar: false,
  closeOnClick: true,
  rtl: false,
  theme: "dark" as const,
};

// Reusable error handler
const handleError = (err: any) => {
  const errorMessage = err instanceof Error 
    ? err.message 
    : err.message?.error?.error_message || "An unexpected error occurred";
  toast.error(errorMessage, TOAST_CONFIG);
  return false;
};

function Picking() {
  const sourceItem = useLoaderData() as SourceItem;
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const materialRequest = searchParams.get('mr_name');
  const itemGroup = searchParams.get('item_group');
  
  // State management
  const [crateCode, setCrateCode] = useState<string | null>(sourceItem.crate_code || null);
  const [hasCrateCode, setHasCrateCode] = useState<boolean>(Boolean(crateCode));
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [itembarcode, setItemBarcode] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [itemIsValidated, setItemIsValidated] = useState<boolean>(false);
  
  const navigate = useNavigate();

  const closeModal = useCallback((): void => {
    setActiveModal(null);
  }, []);

  // Fetch user's active crate
  const getUserActiveCrate = useCallback(async () => {
    setIsLoading(true);
    try {
      const user = await getCurrentUser();
      const params = { user };
      const response = await frappeClient.get('pick_stream.api.get_user_active_crate', params);

      if (response.message.data) {
        setCrateCode(response.message.data);
        setHasCrateCode(true);
      } else {
        setCrateCode(null);
        setHasCrateCode(false);
      }
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeModal === "scan") {
      getUserActiveCrate();
    }
  }, [activeModal, getUserActiveCrate]);

  // Validate crate
  const validateCrate = useCallback(async (crateCode: string): Promise<boolean> => {
    if (!crateCode) return false;
    
    setIsLoading(true);
    try {
      const user = await getCurrentUser();
      const params = {
        user,
        crate_code: crateCode
      };

      const response = await frappeClient.get('pick_stream.api.validate_crate', params);

      if (response.message.data) {
        searchParams.set('crate_code', crateCode);
        setHasCrateCode(true);
        return true;
      }
      return false;
    } catch (err: any) {
      return handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [searchParams]);

  // Skip item
  const skipItem = useCallback(async (closeCrate: boolean): Promise<void> => {
    setIsLoading(true);
    try {
      const user = await getCurrentUser();

      const params = {
        user,
        mr_name: materialRequest,
        item_code: sourceItem?.item_code,
        item_group: itemGroup,
        scanned_qty: 0,
        skipped: true,
        closed_crate: closeCrate,
      };

      await frappeClient.get('pick_stream.api.submit_scan_details', params);
      closeModal();
      navigate(`${location.pathname}${location.search}`, { replace: true });
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [materialRequest, sourceItem?.item_code, itemGroup, closeModal, navigate, location]);

  // Validate barcode
  const validateBarcode = useCallback(async (): Promise<void> => {
    if (!itembarcode) return;
    
    setIsLoading(true);
    try {
      const params = {
        item_code: sourceItem?.item_code,
        barcode: itembarcode
      };

      const response = await frappeClient.get('pick_stream.api.validate_item_against_barcode', params);
      if (response.message.data) {
        setItemIsValidated(response.message.data);
      } else {
        throw new Error('Invalid barcode');
      }
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [itembarcode, sourceItem?.item_code]);

  // Submit scan
  const submitScan = useCallback(async (options: SubmitScanOptions): Promise<void> => {
    const { scannedQuantity = 0, itemType, crates, closeCrate } = options;
    
    setIsLoading(true);
    try {
      const user = await getCurrentUser();

      const params: any = {
        user,
        mr_name: materialRequest,
        item_code: sourceItem?.item_code,
        item_group: itemGroup,
        scanned_qty: scannedQuantity,
        skipped: false,
        closed_crate: closeCrate,
        as_box: false,
        as_other: false,
      };

      if (itemType === "crate") {
        params.crate_code = crateCode;
      } else if (itemType === "box") {
        params.as_box = true;
      } else if (itemType === "other") {
        params.as_other = true;
      } else if (itemType === "crates") {
        params.crates = crates;
        params.scanned_qty = 0;
      }

      const response = await frappeClient.get('pick_stream.api.submit_scan_details', params);
      
      if (response.message.data.complete && (itemType !== "box" && itemType !== "other")) {
        navigate(`/pick_stream/material-requests/`);
        return;
      }

      if (itemType === "box" || itemType === "other") {
        navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
        return;
      }

      closeModal();
      setItemIsValidated(false);
      navigate(`${location.pathname}${location.search}`, { replace: true });
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [materialRequest, sourceItem?.item_code, itemGroup, crateCode, closeModal, navigate, location]);

  return (
    <main className="relative w-full flex flex-col pb-10">
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() => navigate(`/pick_stream/material-requests/${materialRequest}`)}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{sourceItem?.to_warehouse}</p>
      </header>

      <div className="px-4 mt-10">
        {/* Modals */}
        {activeModal === "skip" && 
          <SkipItemModal 
            skipItem={skipItem} 
            closeModal={closeModal} 
            isLoading={isLoading}
          />
        }
        
        {activeModal === "scan" && (
          <>
            {!hasCrateCode ? (
              <>
                <div className="modal-backdrop" onClick={closeModal}></div>
                <div className="modal">
                  <div className="flex flex-col items-center modal-content">
                    <p>Scan Crate</p>

                    <div className="input-container w-full">
                      <input
                        className="input-field mb-0 w-full"
                        name="crate_code"
                        id="crate_code"
                        type="text"
                        placeholder="Crate Code"
                        value={crateCode || ''}
                        onChange={(e) => setCrateCode(e.target.value)}
                      />
                    </div>

                    <button 
                      className="modal-btn" 
                      type="submit" 
                      onClick={() => crateCode && validateCrate(crateCode)}
                      disabled={isLoading}
                    >
                      {isLoading ? 'Checking Availability...' : 'Select Crate'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <ScanItemModal 
                itemCode={sourceItem?.item_code || ''} 
                crateCode={crateCode || ''}
                requestedQuantity={sourceItem?.requested_qty || ''}
                itemDescription={sourceItem?.description || ''}
                itemBarcode={itembarcode}
                setItemBarcode={setItemBarcode}
                validateBarcode={validateBarcode}
                uom={sourceItem?.uom || ''}
                validateCrate={validateCrate}
                itemIsValidated={itemIsValidated}
                submitScan={submitScan} 
                closeModal={closeModal} 
                isLoading={isLoading}
              />
            )}
          </>
        )}
        
        {activeModal === "scanBox" && 
          <ScanAsBoxModal 
            itemCode={sourceItem?.item_code} 
            itemDescription={sourceItem?.description}
            itemBarcode={itembarcode}
            setItemBarcode={setItemBarcode}
            validateBarcode={validateBarcode}
            itemIsValidated={itemIsValidated}
            submitScan={submitScan} 
            closeModal={closeModal} 
            isLoading={isLoading}
          />
        }
        
        {activeModal === "scanOther" && 
          <ScanAsOtherModal 
            itemCode={sourceItem?.item_code} 
            itemDescription={sourceItem?.description}
            itemBarcode={itembarcode}
            setItemBarcode={setItemBarcode}
            validateBarcode={validateBarcode}
            itemIsValidated={itemIsValidated}
            submitScan={submitScan} 
            closeModal={closeModal} 
            isLoading={isLoading}
          />
        }
        
        <div className='text-center w-full mb-6'><p>{sourceItem?.idx} out of {sourceItem?.item_count}</p></div>
        
        <form className="">
          <div className="input-container">
            <label htmlFor="item_code">
              Item Code
              <input
                className="input-field"
                name="item_code"
                id="item_code"
                type="text"
                placeholder="Item Code"
                disabled
                value={sourceItem?.item_code || ''}
              />
            </label>
          </div>

          <div className="input-container">
            <label htmlFor="item_description">
              Description
              <input
                className="input-field"
                name="item_description"
                id="item_description"
                type="text"
                placeholder="Item Description"
                disabled
                value={sourceItem?.description || ''}
              />
            </label>
          </div>
          
          <div className='flex flex-row justify-between items-center'>
            <div className="input-container w-[48%]">
              <label htmlFor="item_uom">
                UOM
                <input
                  className="input-field"
                  name="item_uom"
                  id="item_uom"
                  type="text"
                  placeholder="Unit of Measure"
                  disabled
                  value={sourceItem?.uom || ''}
                />
              </label>
            </div>

            <div className="input-container w-[48%]">
              <label htmlFor="requested_quantity">
                Qty
                <input
                  className="input-field"
                  name="requested_quantity"
                  id="requested_quantity"
                  type="text"
                  placeholder="Requested Quantity"
                  disabled
                  value={sourceItem?.requested_qty || ''}
                />
              </label>
            </div>
          </div>

          <div className="input-container">
            <label htmlFor="from_warehouse">
              From Warehouse
              <input
                className="input-field"
                name="from_warehouse"
                id="from_warehouse"
                type="text"
                placeholder="From Warehouse"
                disabled
                value={sourceItem?.from_warehouse || ''}
              />
            </label>
          </div>
          
          <div className='grid grid-cols-2 grid-rows-2 gap-x-2 gap-y-1'>
            <button 
              className="modal-btn bg-red-700" 
              type="button" 
              onClick={() => setActiveModal("skip")}
            >
              Skip
            </button>
            <button 
              className="modal-btn" 
              type="button" 
              onClick={() => setActiveModal("scan")}
            >
              Scan
            </button>
            <button 
              className="modal-btn" 
              type="button" 
              onClick={() => setActiveModal("scanBox")}
            >
              Box
            </button>
            <button 
              className="modal-btn" 
              type="button" 
              onClick={() => setActiveModal("scanOther")}
            >
              Other
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

export default Picking;

export async function pickingViewLoader({request}: LoaderFunctionArgs) {
  try {
    const url = new URL(request.url); 
    const user = await getCurrentUser();
    const mr_name = url.searchParams.get('mr_name');
    const item_group = url.searchParams.get('item_group');
    const crate_code = url.searchParams.get('crate_code');
    
    if (!user || !mr_name || !item_group) {
      return redirect('/pick_stream/material-requests/');
    }
    
    const sourceItem = await getPickingViewItem(user, mr_name, item_group, crate_code || '');

    if (!sourceItem || (Object.keys(sourceItem).length === 0 && sourceItem.constructor === Object)) {
      return redirect('/pick_stream/material-requests/');
    }
    
    return sourceItem;
  } catch (error) {
    console.error('Error loading picking view:', error);
    return redirect('/pick_stream/material-requests/');
  }
}
