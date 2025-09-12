import { useState, useEffect, useCallback } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
  LoaderFunctionArgs, 
  useLocation,
  redirect
} from 'react-router';
import { FaArrowLeft, FaBarcode, FaBox, FaEllipsisH, FaTimes } from 'react-icons/fa';
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
  const skipItem = useCallback(async (): Promise<void> => {
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
  const validateBarcode = useCallback(async (itemCode: string, barcode: string): Promise<void> => {
    if (!barcode) return;
    
    setIsLoading(true);
    try {
      const params = {
        item_code: itemCode,
        barcode: barcode
      };

      const response = await frappeClient.get('pick_stream.api.validate_item_against_barcode', params);
      if (response.message.data) {
        setItemIsValidated(response.message.data);
      } else {
        throw new Error('Invalid barcode');
      }
    } catch (err: any) {
      handleError(err);
      // Re-throw the error so the modal can handle it properly
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Submit scan
  const submitScan = useCallback(async (options: SubmitScanOptions): Promise<void> => {
    const { scannedQuantity = 0, itemType, crates } = options;
    
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
        navigate(`/pick_stream/material-requests/${materialRequest}`);
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
    <main className="relative w-full flex flex-col bg-gray-50">
      {/* Header */}
      <header className='flex flex-row items-center px-4 py-4 bg-white shadow-sm border-b border-gray-200'>
        <button 
          onClick={() => navigate(`/pick_stream/material-requests/${materialRequest}`)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <FaArrowLeft size={20} className="text-gray-700"/>
        </button>

        <div className="flex-1 text-center">
          <h1 className='text-lg font-semibold text-gray-900'>{sourceItem?.to_warehouse}</h1>
          <p className='text-sm text-gray-500 mt-1'>
            Item {sourceItem?.idx} of {sourceItem?.item_count}
          </p>
        </div>
      </header>

      <div className="flex-1 px-4 py-6">
        {/* Modals */}
        {activeModal === "skip" && 
          <SkipItemModal 
            skipItem={skipItem}
            closeModal={closeModal} 
            isLoading={isLoading}
            itemCode={sourceItem?.item_code || ''} 
            itemDescription={sourceItem?.description}
          />
        }
        
        {activeModal === "scan" && (
          <>
{!hasCrateCode ? (
  <>
    {/* Blurred backdrop */}
    <div 
      className="fixed inset-0 z-40" 
      onClick={closeModal}
      style={{
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        backgroundColor: 'rgba(0, 0, 0, 0.3)'
      }}
    ></div>
    
    {/* Modal container */}
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-auto shadow-2xl border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Scan Crate</h3>
          <button 
            onClick={closeModal} 
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <FaTimes className="text-gray-500" />
          </button>
        </div>

        <div className="mb-4">
          <label htmlFor="crate_code" className="block text-sm font-medium text-gray-700 mb-2">
            Crate Code
          </label>
          <input
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none placeholder-gray-500"
            name="crate_code"
            id="crate_code"
            type="text"
            placeholder="Enter crate code"
            value={crateCode || ''}
            onChange={(e) => setCrateCode(e.target.value)}
          />
        </div>

        <button 
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          type="submit" 
          onClick={() => crateCode && validateCrate(crateCode)}
          disabled={isLoading || !crateCode}
        >
          {isLoading ? (
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            'Select Crate'
          )}
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
            requestedQuantity={sourceItem?.requested_qty || ''}
            uom={sourceItem?.uom || ''}
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
            itemCode={sourceItem?.item_code || ''} 
            requestedQuantity={sourceItem?.requested_qty || ''}
            uom={sourceItem?.uom || ''}
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
        
        {/* Item Details Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Item Details</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Item Code</label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900">
                {sourceItem?.item_code || '-'}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900 leading-relaxed">
                {sourceItem?.description || '-'}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">UOM</label>
                <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900">
                  {sourceItem?.uom || '-'}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
                <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900 font-medium">
                  {sourceItem?.requested_qty || '-'}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">From Warehouse</label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-900">
                {sourceItem?.from_warehouse || '-'}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
          
          {/* Primary Actions */}
          <div className="grid grid-cols-2 gap-4">
            <button 
              className="flex items-center justify-center space-x-3 bg-blue-600 text-white py-6 px-6 rounded-xl font-semibold text-lg hover:bg-blue-700 active:scale-[0.98] transition-all shadow-md" 
              type="button" 
              onClick={() => setActiveModal("scan")}
            >
              <FaBarcode size={24} />
              <span>Scan Item</span>
            </button>
            
            <button 
              className="flex items-center justify-center space-x-3 bg-red-600 text-white py-6 px-6 rounded-xl font-semibold text-lg hover:bg-red-700 active:scale-[0.98] transition-all shadow-md" 
              type="button" 
              onClick={() => setActiveModal("skip")}
            >
              <FaTimes size={24} />
              <span>Skip Item</span>
            </button>
          </div>

          {/* Secondary Actions */}
          <div className="grid grid-cols-2 gap-4">
            <button 
              className="flex items-center justify-center space-x-3 bg-gray-600 text-white py-5 px-6 rounded-xl font-semibold hover:bg-gray-700 active:scale-[0.98] transition-all shadow-md" 
              type="button" 
              onClick={() => setActiveModal("scanBox")}
            >
              <FaBox size={22} />
              <span>Scan as Box</span>
            </button>
            
            <button 
              className="flex items-center justify-center space-x-3 bg-gray-600 text-white py-5 px-6 rounded-xl font-semibold hover:bg-gray-700 active:scale-[0.98] transition-all shadow-md" 
              type="button" 
              onClick={() => setActiveModal("scanOther")}
            >
              <FaEllipsisH size={22} />
              <span>Scan as Other</span>
            </button>
          </div>
        </div>
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