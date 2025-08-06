import { useState, useCallback } from 'react';

type ScanAsBoxModalProps = {
  itemCode: string;
  itemDescription: string;
  itemBarcode: string;
  setItemBarcode: (value: string) => void;
  validateBarcode: (itemCode: string, itemBarcode: string) => Promise<void>;
  itemIsValidated: boolean;
  submitScan: (options: {
    scannedQuantity: number;
    itemType: string;
    closeCrate?: boolean;
  }) => Promise<void>;
  closeModal: () => void;
  isLoading?: boolean; // Add isLoading prop
};

export default function ScanAsBoxModal({
  itemCode,
  itemDescription,
  itemBarcode,
  setItemBarcode,
  validateBarcode,
  itemIsValidated,
  submitScan,
  closeModal
}: ScanAsBoxModalProps) {
  const [scannedQuantity, setScannedQuantity] = useState<number>(0); 
  const [closeCrate, setCloseCrate] = useState(false);
  
  const handleSubmitScan = useCallback(() => {
    submitScan({scannedQuantity, itemType: "box", closeCrate});
  }, [submitScan, scannedQuantity, closeCrate]);
  
  const handleVerifyBarcode = useCallback(() => {
    validateBarcode(itemCode, itemBarcode);
  }, [validateBarcode, itemCode, itemBarcode]);

  return (
    <>
    <div className="modal-backdrop" onClick={closeModal}></div>
    <div className="modal" role="dialog" aria-modal="true">
      {itemIsValidated ? (
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
                min={1}
                onChange={(e) => setScannedQuantity(parseInt(e.target.value) || 0)}
                aria-label="Scanned Quantity"
              />
            </label>
          </div>

          <button 
            className="modal-btn" 
            type="button" 
            onClick={handleSubmitScan}
          >
            Submit Scan
          </button>
        </div>
      ) : (    
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
                aria-label="Item Barcode"
              />
            </label>
          </div>

          <button 
            className="modal-btn" 
            type="button" 
            onClick={handleVerifyBarcode}
          >
            Verify Barcode
          </button>
        </div>
      )}
    </div>
    </>
  );
}
