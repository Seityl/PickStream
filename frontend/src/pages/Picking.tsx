import { useState } from 'react';
import { 
  useNavigate, 
  useSearchParams, 
  useLoaderData, 
  LoaderFunctionArgs, 
  useLocation,
  useRevalidator
} from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';
import { FaSpinner } from "react-icons/fa6";
import {getPickingViewItem} from '../../utils/api';
import {frappeClient} from '../../utils/client';
import { useAuth } from '../context/AuthContext';
import SkipItemModal from '../components/SkipItemModal';
import ScanItemModal from '../components/ScanItemModal';
import ScanAsBoxModal from '../components/ScanAsBoxModal';
import ScanAsOtherModal from '../components/ScanAsOtherModal';

type SourceItem = {
  item_code: string;
  description: string;
  requested_qty: string;
  uom: string;
  from_warehouse: string;
};

function Picking() {
  const {user} = useAuth();
  const revalidator = useRevalidator();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const materialRequest = searchParams.get('mr_name');
  const itemGroup = searchParams.get('item_group');
  const crateCode = searchParams.get('crate_code');
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [isHidden, setIsHidden] = useState(true);
  const sourceItem = useLoaderData();
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


  function openModal(modalType: string): void {
    setActiveModal(modalType);
  }

  function closeModal(): void {
    setActiveModal(null);
  }

  async function skipItem(closeCrate: boolean): Promise<void> {
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
    revalidator.revalidate();
  }
  
  async function validateBarcode(itemCode: string, itemBarcode: string): Promise<void>  {
    const params = {
      item_code: sourceItem?.item_code,
      barcode: itemBarocde
    }
    const response = await frappeClient.get('pick_stream.api.validate_item_against_barcode', params);

    setItemIsValidated(response.message.data);
  }

  async function submitScan(scannedQuantity: number, itemType: string = "", closeCrate: boolean): Promise<void> {
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
      params["crate_code"] = searchParams.get('crate_code')!;
    } else if (itemType === "box") {
      params.as_box = true;
    } else if (itemType === "other") {
      params.as_other = true;
    }

    const response = await frappeClient.get('pick_stream.api.submit_scan_details', params);

    if (itemType === "box") {
      navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
    } else if (itemType === "other") {
      navigate(`/pick_stream/printers?mr_name=${materialRequest}&item_code=${sourceItem?.item_code}&item_type=${itemType}`);
    }
    console.log(response);
    closeModal()
    setItemIsValidated(false);
    revalidator.revalidate();
  }

  return (
    <main className="relative min-h-screen w-full flex flex-col pb-10">
      <div className="h-full flex flex-col justify-center items-center" hidden={revalidator.state === "idle"}>
        <FaSpinner size={32}/>
      </div> 

      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() =>navigate(`/pick_stream/material-requests/${materialRequest}`)}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{crateCode}</p>
      </header>

      <div className="px-4 mt-10">
        {activeModal === "skip" && 
        <SkipItemModal 
          skipItem={skipItem} 
          closeModal={closeModal} 
        />
        }
        {activeModal === "scan" && 
        <ScanItemModal 
          itemCode={sourceItem?.item_code} 
          itemBarcode={itemBarocde}
          setItemBarcode={setItemBarcode}
          validateBarcode={validateBarcode}
          itemIsValidated={itemIsValidated}
          submitScan={submitScan} 
          closeModal={closeModal} 
        />
        }
        {activeModal === "scanBox" && 
        <ScanAsBoxModal 
          itemCode={sourceItem?.item_code} 
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
          itemBarcode={itemBarocde}
          setItemBarcode={setItemBarcode}
          validateBarcode={validateBarcode}
          itemIsValidated={itemIsValidated}
          submitScan={submitScan} 
          closeModal={closeModal} 
        />
        }
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

          <div className="input-container">
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


          <div className="input-container">
            <label htmlFor="requested_quantity">
              Requested Quantity
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
              Scan as Box
            </button>
            <button className="modal-btn" type="button" onClick={() => setActiveModal("scanOther")}>
              Scan as Other
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
  const user = localStorage.getItem('user');
  const mr_name = url.searchParams.get('mr_name');
  const item_group = url.searchParams.get('item_group');
  const crate_code = url.searchParams.get('crate_code');
  return await getPickingViewItem(user!, mr_name!, item_group!, crate_code!);
}
