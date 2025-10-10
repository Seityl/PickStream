import { useState, useEffect, useCallback } from 'react';
import {
  useNavigate,
  useSearchParams,
  useLoaderData,
  LoaderFunctionArgs,
  useLocation,
  redirect,
  useNavigation
} from 'react-router';
import { FaArrowLeft, FaBarcode, FaBox, FaEllipsisH, FaTimes } from 'react-icons/fa';
import { getPickingViewItem } from '../../utils/api';
import { frappeClient } from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import SkipItemModal from '../components/SkipItemModal';
import ScanItemModal from '../components/ScanItemModal';
import ScanAsBoxModal from '../components/ScanAsBoxModal';
import ScanAsOtherModal from '../components/ScanAsOtherModal';
import PageLoader from '../components/PageLoader';
import { toast } from 'react-toastify';

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
  const navigation = useNavigation();

  const [searchParams] = useSearchParams();
  const materialRequest = searchParams.get('mr_name');
  const itemGroup = searchParams.get('item_group');

  // State management
  const [crateCode, setCrateCode] = useState<string | null>(sourceItem?.crate_code || null);
  const [hasCrateCode, setHasCrateCode] = useState<boolean>(Boolean(crateCode));
  const [crateScanInput, setCrateScanInput] = useState<string>(''); // Separate state for input field
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [itembarcode, setItemBarcode] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [itemIsValidated, setItemIsValidated] = useState<boolean>(false);
  const [isRedirecting, setIsRedirecting] = useState<boolean>(false);
  const [isLoadingActiveCrate, setIsLoadingActiveCrate] = useState<boolean>(false);

  const navigate = useNavigate();

  const closeModal = useCallback((): void => {
    setActiveModal(null);
  }, []);

  // Fetch user's active crate
  const getUserActiveCrate = useCallback(async () => {
    setIsLoadingActiveCrate(true);
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
      setIsLoadingActiveCrate(false);
    }
  }, []);

  useEffect(() => {
    if (activeModal === "scan") {
      getUserActiveCrate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeModal]);

  // Validate crate
  const validateCrate = useCallback(async (crateCodeToValidate: string): Promise<boolean> => {
    if (!crateCodeToValidate) return false;
    
    setIsLoading(true);
    try {
      const user = await getCurrentUser();
      const params = {
        user,
        crate_code: crateCodeToValidate
      };

      const response = await frappeClient.get('pick_stream.api.validate_crate', params);

      if (response.message.data) {
        // Crate is available - set it as active and proceed
        setCrateCode(crateCodeToValidate);
        setHasCrateCode(true);
        setCrateScanInput(''); // Clear the input field
        return true;
      } else {
        // Crate exists but is not available (closed, in transit, etc.)
        toast.warning(
          `Crate '${crateCodeToValidate}' is not available for use. Please scan a different crate.`,
          TOAST_CONFIG
        );
        // Clear only the input field, preserve active crate state
        setCrateScanInput('');
        return false;
      }
    } catch (err: any) {
      // This handles validation errors (e.g., crate in use by another user)
      handleError(err);
      // Clear only the input field, preserve active crate state
      setCrateScanInput('');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

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
      // Use a small delay to ensure state updates complete before navigation
      setTimeout(() => {
        navigate(`${location.pathname}${location.search}`, { replace: true });
      }, 0);
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [materialRequest, sourceItem?.item_code, itemGroup, closeModal, navigate, location]);

  // Validate barcode
  const validateBarcode = useCallback(async (itemCode: string, barcode: string): Promise<boolean> => {
    if (!barcode) return false;

    setIsLoading(true);
    try {
      const params = {
        item_code: itemCode,
        barcode: barcode
      };

      const response = await frappeClient.get('pick_stream.api.validate_item_against_barcode', params);
      if (response.message.data) {
        setItemIsValidated(response.message.data);
        return true;
      } else {
        handleError(new Error('Invalid barcode'));
        return false;
      }
    } catch (err: any) {
      handleError(err);
      return false;
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
      
      // CRITICAL FIX: Update crate state after submitting multiple crates
      // When scanning with multiple crates, the last crate becomes the active one
      if (itemType === "crates" && crates && crates.length > 0) {
        const activeCrate = crates[crates.length - 1].crate_code;
        setCrateCode(activeCrate);
        setHasCrateCode(true);
      }
      
      if (response.message.data.complete && (itemType !== "box" && itemType !== "other")) {
        closeModal();
        setIsRedirecting(true);
        toast.success("Pick list completed successfully! Redirecting...", {
          ...TOAST_CONFIG,
          autoClose: 2000,
        });
        // Small delay to let the user see the success message
        setTimeout(() => {
          navigate(`/pick_stream/material-requests/${materialRequest}`);
        }, 500);
        return;
      }

      if (itemType === "box" || itemType === "other") {
        navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
        return;
      }

      closeModal();
      setItemIsValidated(false);
      setItemBarcode('');
      // Use a small delay to ensure state updates complete before navigation
      setTimeout(() => {
        navigate(`${location.pathname}${location.search}`, { replace: true });
      }, 0);
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [materialRequest, sourceItem?.item_code, itemGroup, crateCode, closeModal, navigate, location]);
  // NOW you can do the conditional return
  if (navigation.state === "loading") {
    return <PageLoader variant="default" />;
  }
  return (
    <main className="relative w-full flex flex-col bg-gray-50">
      {/* Redirecting Overlay */}
      {isRedirecting && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center"
          style={{
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            backgroundColor: 'rgba(0, 0, 0, 0.4)'
          }}
        >
          <div className="bg-white rounded-2xl p-8 shadow-2xl max-w-sm mx-4 text-center">
            <div className="mb-4">
              <div className="w-16 h-16 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Pick List Complete!</h3>
            <p className="text-gray-600">Redirecting you back...</p>
          </div>
        </div>
      )}

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

        {isLoadingActiveCrate ? (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm text-blue-800 font-medium">Fetching your active crate...</p>
            </div>
          </div>
        ) : (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              {crateCode
                ? `Current active crate: ${crateCode}. Scan a new crate to change it.`
                : 'You have no active crate currently. Scan a crate to set it active.'}
            </p>
          </div>
        )}

        <div className="mb-4">
          <input
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none placeholder-gray-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50"
            name="crate_code"
            id="crate_code"
            type="text"
            placeholder={isLoadingActiveCrate ? "Loading..." : "Enter crate code"}
            value={crateScanInput}
            onChange={(e) => setCrateScanInput(e.target.value)}
            disabled={isLoadingActiveCrate}
            autoFocus={!isLoadingActiveCrate}
          />
        </div>

        <button
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          type="submit"
          onClick={() => crateScanInput && validateCrate(crateScanInput)}
          disabled={isLoading || !crateScanInput || isLoadingActiveCrate}
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
    isLoadingActiveCrate={isLoadingActiveCrate}
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