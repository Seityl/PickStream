import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';
import {frappeClient} from '../../utils/client';
import { useAuth } from '../context/AuthContext';


type CrateItem = {
  item_code: string;
};

type SourceItem = {
  item_code: string;
  description: string;
  requested_qty: string;
  uom: string;
  from_warehouse: string;
};

export default function Picking() {
  const {user} = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isHidden, setIsHidden] = useState(true);
  const [sourceItem, setSourceItem] = useState<SourceItem | null>(null)
  const [itemBarocde, setItemBarcode] = useState('');
  const [scannedQuantity, setScannedQuantity] = useState(0);
  const navigate = useNavigate();
  const routeParams = useParams();
  function toggleModal() {
    setIsHidden((prevState) => {
      return !prevState;
    });
  }

  // function backToMaterialRequest() {
  //   navigate(`/pick_stream/material-requests/$`);
  // }

  async function submitScan() {
    const params = {
      user: user,
      mr_name: routeParams.material_request,
      item_code: sourceItem?.item_code,
      item_group: searchParams.get('item_group'),
      crate_code: searchParams.get('crate_code'),
      scanned_qty: scannedQuantity,
    };
    const response = await frappeClient.post('pick_stream.api.submit_scan_details', params);

    console.log(response)
    toggleModal();
  }
  useEffect(() => {
    const fetchPickingItem= async function() {
      const params = {
        user: user,
        mr_name: routeParams.material_request,
        item_group: searchParams.get('item_group')
      };
      const response = await frappeClient.get('pick_stream.api.get_material_request_picking_view', params);

      console.log(response.message.data);
      setSourceItem(response.message.data);
    }
    fetchPickingItem();
  }, [])

  return (
    <main className="relative min-h-screen w-full flex flex-col pb-10">
      <header className="flex flex-row justify-between items-center px-4 py-6 mb-10 bg-gray-200">
        <button className="cursor-pointer">
          <FaArrowLeft />
        </button>

        <p>MAT-MR-2025-01390</p>
      </header>

      <div className="px-4">
        <form className="">
          {!isHidden ? (
            <div className="modal">
              <div className="modal-backdrop" onClick={submitScan}></div>

              <div className="flex flex-col items-center modal-content">
                <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
                  {sourceItem?.item_code}
                </p>

                <div className="input-container w-full">
                  <label htmlFor="item_barcode">
                    Item BarCode 
                    <input
                      className="input-field mb-0"
                      name="item_barcode"
                      id="item_barcode"
                      type="text"
                      placeholder="Item Barcode"
                      value={itemBarocde}
                      onChange={(e) => setItemBarcode(e.target.value)}
                    />
                  </label>
                </div>

                <div className="input-container w-full">
                  <label htmlFor="scanned_quantity">
                    Scanned Quantity
                    <input
                      className="input-field mb-0"
                      name="scanned_quantity"
                      id="scanned_quantity"
                      type="number"
                      placeholder="Scanned Quantity"
                      value={scannedQuantity}
                      onChange={(e) => setScannedQuantity(parseInt(e.target.value))}
                    />
                  </label>
                </div>

                <button className="scan-btn" type="submit" onClick={toggleModal}>
                  Submit Scan
                </button>
              </div>
            </div>
          ) : (
            ''
          )}

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
              Item Description
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
              Unit of Measure
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

          <button className="scan-btn" type="button" onClick={toggleModal}>
            Scan
          </button>
        </form>
      </div>
    </main>
  );
}
