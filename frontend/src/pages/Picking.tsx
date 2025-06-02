import { useState, useEffect } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
  LoaderFunctionArgs, 
  useLocation,
  redirect
} from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';
import { FaSpinner } from "react-icons/fa6";
import {getPickingViewItem} from '../../utils/api';
import {frappeClient} from '../../utils/client';
import { getCurrentUser } from '../../utils/auth';
import { useAuth } from '../context/AuthContext';
import SkipItemModal from '../components/SkipItemModal';
import ScanItemModal from '../components/ScanItemModal';
import ScanAsBoxModal from '../components/ScanAsBoxModal';
import ScanAsOtherModal from '../components/ScanAsOtherModal';
import { nav, p } from 'motion/react-client';
import { toast } from 'react-toastify';

type SourceItem = {
  item_code: string;
  description: string;
  requested_qty: string;
  uom: string;
  from_warehouse: string;
};

type submitScanOptions = {
  scannedQuantity: number;
  itemType: string;
  crates?: Array<{ scanned_qty: number; crate_code: string; uom: string }>;
  closeCrate?: boolean;
};


function Picking() {
  const sourceItem = useLoaderData();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const materialRequest = searchParams.get('mr_name');
  const itemGroup = searchParams.get('item_group');
  const [crateCode, setCrateCode] = useState(sourceItem.crate_code || null);
  const [hasCrateCode, setHasCrateCode] = useState(Boolean(crateCode));
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [isHidden, setIsHidden] = useState(true);
  // const [sourceItem, setSourceItem] = useState<SourceItem | null>(null)
  const [itemBarocde, setItemBarcode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState('');
  const [itemIsValidated, setItemIsValidated] = useState(false);
  const [scannedQuantity, setScannedQuantity] = useState(0);
  const navigate = useNavigate();
 
  function toggleModal() {
    setIsHidden((prevState) => {
      return !prevState;
    });
  }

  function toggleCrateModal() {
    setHasCrateCode((prevState) => {
      return !prevState;
    });
  }

  function closeModal(): void {
    setActiveModal(null);
  }

  async function getUserActiveCrate() {
    try {
        const params = {
          user: await getCurrentUser()
        };
        const response = await frappeClient.get('pick_stream.api.get_user_active_crate', params);

        if (response.message.data) {
          console.log(typeof response.message.data, '- if block');
          setCrateCode(response.message.data);
          setHasCrateCode(true);
        } else {
          console.log(typeof response.message.data, '- else block');
          setCrateCode(null);
          setHasCrateCode(false);
        }
      }catch (err: any) {
        toast.error(err.message.error.error_message,  {});
      }
  }

  useEffect(() => {
    if (activeModal === "scan") {
      getUserActiveCrate();
    } 
  }, [activeModal]);

  async function validateCrate(crateCode: string): Promise<boolean> {
    const params = {
      user: await getCurrentUser(),
      crate_code: crateCode
    };

    try {
      const response = await frappeClient.get('pick_stream.api.validate_crate', params);

      if (response.message.data) {
        searchParams.set('crate_code', crateCode!);
        setHasCrateCode(true);
        toggleModal();
        return true; // <-- ✅ Return success
      }

      toggleModal();
      return false; // <-- ✅ Explicitly return failure if no data
    } catch(err: any) {
      toast.error(err.message?.error?.error_message || "Crate validation failed", {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true,
        rtl: false,
        theme: "dark",
      });
      return false; // <-- ✅ Return failure on error
    }
  }

  // async function validateCrate(crateCode: string) {
  //   const params = {
  //     user: await getCurrentUser(),
  //     crate_code: crateCode
  //   };

  //   try {
  //     const response = await frappeClient.get('pick_stream.api.validate_crate', params);
    
  //     if (response.message.data) {
  //       searchParams.set('crate_code', crateCode!);
  //       setHasCrateCode(true);
  //     }
      
  //     toggleModal();
  //   } catch(err: any) {
  //     toast.error(err.message.error.error_message,  {
  //       position: "bottom-right",
  //       autoClose: 5000,
  //       hideProgressBar: false,
  //       closeOnClick: true, 
  //       rtl: false,
  //       theme: "dark",
  //     })
  //   }
    
  // }

  async function skipItem(closeCrate: boolean): Promise<void> {
    try {
      const user = await getCurrentUser();

      const params = {
        user: user,
        mr_name: materialRequest,
        item_code: sourceItem?.item_code,
        item_group: itemGroup,
        scanned_qty: 0,
        skipped: true,
        closed_crate: closeCrate,
      };

      const response = await frappeClient.get('pick_stream.api.submit_scan_details', params);
      closeModal();
      navigate(`${location.pathname}${location.search}`, { replace: true });
    } catch(err: any) {
      toast.error(err.message.error.error_message,  {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
      })
    }
  }
  
  async function validateBarcode(itemCode: string, itemBarcode: string): Promise<void>  {
    try {
      const params = {
      item_code: sourceItem?.item_code,
      barcode: itemBarocde
      };

      const response = await frappeClient.get('pick_stream.api.validate_item_against_barcode', params);
      if (response.message.data) {
        setItemIsValidated(response.message.data);
      } else {
        throw new Error('Invalid barcode');
      }
    } catch (err: any) {
        toast.error(err instanceof Error ? err.message : err.message.error.error_message,  {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
      })
    }
  }

  async function submitScan(options: submitScanOptions): Promise<void> {
    const { scannedQuantity = 0, itemType, crates, closeCrate } = options;
    const user = await getCurrentUser();

    const params: any = {
      user: user,
      mr_name: materialRequest,
      item_code: sourceItem?.item_code,
      item_group: searchParams.get('item_group'),
      scanned_qty: scannedQuantity,
      skipped: false,
      closed_crate: closeCrate,
      as_box: false,
      as_other: false,
    };

    if (itemType === "crate") {
      params["crate_code"] = crateCode;
    } else if (itemType === "box") {
      params.as_box = true;
    } else if (itemType === "other") {
      params.as_other = true;
    } else if (itemType === "crates") {
      params["crates"] = crates;
      params["scanned_qty"] = 0;
    }


    try {
      console.log(params, 'params from submit scan details');
      const response = await frappeClient.get('pick_stream.api.submit_scan_details', params);
      console.log(response, 'response from submit scan details');
      if (response.message.data.complete && (itemType !== "box" && itemType !== "other")) {
        navigate(`/pick_stream/material-requests/`);
        return;
      }

      if (itemType === "box") {
        return navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
      } else if (itemType === "other") {
        return navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
      }

      closeModal()
      setItemIsValidated(false);

      console.log('response outside if block', response);
      navigate(`${location.pathname}${location.search}`, { replace: true });
    } catch(err: any) {
      toast.error(err.message.error.error_message,  {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
      })
    }
  }

  return (
    <main className="relative w-full flex flex-col pb-10">

      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() =>navigate(`/pick_stream/material-requests/${materialRequest}`)}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{sourceItem?.to_warehouse}</p>
      </header>

      <div className="px-4 mt-10">

        {activeModal === "skip" && 
        <SkipItemModal 
          skipItem={skipItem} 
          closeModal={closeModal} 
        />
        }
        {activeModal === "scan" && 
        (
          <>
            {!hasCrateCode ? 
              <>
                <div className="modal-backdrop" onClick={() => setActiveModal(null)}></div>

                <div className="modal">
                  <div className="flex flex-col items-center modal-content">
                    <p className=''>Scan Crate</p>

                    <div className="input-container w-full">
                        <input
                          className="input-field mb-0 w-full"
                          name="crate_code"
                          id="crate_code"
                          type="text"
                          placeholder="Crate Code"
                          value={crateCode!}
                          onChange={(e) => {setCrateCode(e.target.value);}}
                        />
                    </div>

                    <button className="modal-btn" type="submit" onClick={() => validateCrate(crateCode)}>
                    {!isLoading ? 'Select Crate' : 'Checking Availability...'}
                    </button>
                  </div>
                </div>
              </>
              :  
                <ScanItemModal 
                itemCode={sourceItem?.item_code} 
                crateCode={crateCode}
                requestedQuantity={sourceItem?.requested_qty}
                itemDescription={sourceItem?.description}
                itemBarcode={itemBarocde}
                setItemBarcode={setItemBarcode}
                validateBarcode={validateBarcode}
                uom={sourceItem?.uom}
                validateCrate={validateCrate}
                itemIsValidated={itemIsValidated}
                submitScan={submitScan} 
                closeModal={closeModal} 
              />
            }  
          </>
        )
        }
        {activeModal === "scanBox" && 
        <ScanAsBoxModal 
          itemCode={sourceItem?.item_code} 
          itemDescription={sourceItem?.description}
          itemBarcode={itemBarocde}
          setItemBarcode={setItemBarcode}
          validateBarcode={validateBarcode}
          itemIsValidated={itemIsValidated}
          submitScan={submitScan} 
          closeModal={closeModal} 
        />
        }
        {activeModal === "scanOther" && 
        <ScanAsOtherModal 
          itemCode={sourceItem?.item_code} 
          itemDescription={sourceItem?.description}
          itemBarcode={itemBarocde}
          setItemBarcode={setItemBarcode}
          validateBarcode={validateBarcode}
          itemIsValidated={itemIsValidated}
          submitScan={submitScan} 
          closeModal={closeModal} 
        />
        }
        <div className='text-center w-full mb-6'><p>{sourceItem?.idx} out of {sourceItem?.item_count}</p></div>
        <form className="">
          {/* <div className="input-container">
            <label htmlFor="to_warehouse">
              To Warehouse
              <input
                className="input-field"
                name="to_warehouse"
                id="to_warehouse0"
                type="text"
                placeholder="To Warehouse"
                disabled
                value={}
              />
            </label>
          </div> */}

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
                value={sourceItem?.item_code}
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
                value={sourceItem?.description}
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
                  value={sourceItem?.uom}
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
                  value={sourceItem?.requested_qty}
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
                value={sourceItem?.from_warehouse}
              />
            </label>
          </div>
          
          <div className='grid grid-cols-2 grid-rows-2 gap-x-2 gap-y-1'>
            <button className="modal-btn bg-red-700" type="button" onClick={() => setActiveModal("skip")}>
              Skip
            </button>
            <button className="modal-btn" type="button" onClick={() => setActiveModal("scan")}>
              Scan
            </button>
            <button className="modal-btn" type="button" onClick={() => setActiveModal("scanBox")}>
              Box
            </button>
            <button className="modal-btn" type="button" onClick={() => setActiveModal("scanOther")}>
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
  const url = new URL(request.url); 
  const user = await getCurrentUser();
  const mr_name = url.searchParams.get('mr_name');
  const item_group = url.searchParams.get('item_group');
  const crate_code = url.searchParams.get('crate_code');
  const sourceItem = await getPickingViewItem(user!, mr_name!, item_group!, crate_code!);

  if (Object.keys(sourceItem).length === 0 && sourceItem.constructor === Object) {
    return redirect('/pick_stream/material-requests/');
  }
  return sourceItem;
}
