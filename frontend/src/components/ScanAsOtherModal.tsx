import {useState} from 'react';

export default function ScanAsOtherModal({itemCode, itemDescription, itemBarcode, setItemBarcode, validateBarcode, itemIsValidated, submitScan, closeModal}: any) {
  const [scannedQuantity, setScannedQuantity] = useState<number>(0); 
  const [closeCrate, setCloseCrate] = useState(false);

  return (
    <>
    <div className="modal-backdrop" onClick={closeModal}></div>
    <div className="modal">
      {itemIsValidated ? 
      
      <div className="flex flex-col items-center modal-content">
        <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
          {itemCode} : {itemDescription}
        </p>

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

        <button className="modal-btn" type="submit" onClick={() => submitScan({scannedQuantity: scannedQuantity, itemType: "other", closeCrate: closeCrate})}>
          Submit Scan
        </button>
      
      </div>
      :    
      <div className="flex flex-col items-center modal-content">
        <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
          {itemCode}
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
              value={itemBarcode}
              onChange={(e) => setItemBarcode(e.target.value)}
            />
          </label>
        </div>

        <button className="modal-btn" type="submit" onClick={validateBarcode}>
          Verify Barcode
        </button>
      
      </div>
      }
    </div>
    </>
  )
}
