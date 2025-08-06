import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';

type CrateItem = {
  scanned_qty: number;
  crate_code: string;
  uom: string;
};

type SubmitScanOptions = {
  scannedQuantity: number;
  itemType: string;
  crates?: Array<{ scanned_qty: number; crate_code: string; uom: string }>;
  closeCrate?: boolean;
};

type ScanItemModalProps = {
  itemCode: string;
  crateCode: string;
  requestedQuantity: string;
  uom: string;
  itemDescription: string;
  itemBarcode: string;
  setItemBarcode: (value: string) => void;
  validateBarcode: (itemCode: string, itemBarcode: string) => Promise<void>;
  validateCrate: (crateCode: string) => Promise<boolean>;
  itemIsValidated: boolean;
  submitScan: (options: SubmitScanOptions) => Promise<void>;
  closeModal: () => void;
  isLoading?: boolean;
};

export default function ScanItemModal({
  itemCode,
  crateCode,
  requestedQuantity,
  uom,
  itemDescription,
  itemBarcode,
  setItemBarcode,
  validateBarcode,
  validateCrate,
  itemIsValidated,
  submitScan,
  closeModal
}: ScanItemModalProps) {
  const [scannedQuantity, setScannedQuantity] = useState<number>(0);
  const [closeCrate, setCloseCrate] = useState(false);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [crates, setCrates] = useState<CrateItem[]>([{scanned_qty: scannedQuantity, crate_code: crateCode, uom: uom || 'EACH'}]);
  const [isHidden, setIsHidden] = useState(true);
  const navigate = useNavigate();

  const addCrate = useCallback(() => {
    setIsHidden(false);
  }, []);

  const addToTable = useCallback(async () => {
    if (!input.trim()) {
      return;
    }
    
    setIsLoading(true);
    try {
      const crateIsValid = await validateCrate(input);

      if (input !== crateCode && crateIsValid) {
        setCrates((prevCrates) => [...prevCrates, {scanned_qty: 0, crate_code: input, uom: uom || 'EACH'}]);
        setInput('');
        setIsHidden(true);
      }
    } catch (error) {
      console.error('Error validating crate:', error);
    } finally {
      setIsLoading(false);
    }
  }, [input, crateCode, validateCrate, uom]);

  const handleQuantityChange = useCallback((index: number, value: string) => {
    const userInput = value;
    const newCrates = [...crates];
    
    if (userInput === '' || !isNaN(Number(userInput))) {
      newCrates[index].scanned_qty = userInput === '' ? 0 : Number(userInput);
      setCrates(newCrates);
    }
  }, [crates]);

  const handleSubmitScan = useCallback((options: {
    scannedQuantity: number;
    itemType: string;
    crates?: CrateItem[];
    closeCrate?: boolean;
  }) => {
    submitScan(options);
  }, [submitScan]);

  const handleVerifyBarcode = useCallback(() => {
    validateBarcode(itemCode, itemBarcode);
  }, [validateBarcode, itemCode, itemBarcode]);

  return (
    <>
    {!isHidden ? (
      <>
        <div className="modal-backdrop" onClick={() => setIsHidden(true)}></div>
        <div className="modal" role="dialog" aria-modal="true">
          <div className="flex flex-col items-center modal-content">
            <p className=''>Scan Crate</p>

            <div className="input-container w-full">
              <input
                className="input-field mb-0 w-full"
                name="crate_code"
                id="crate_code"
                type="text"
                placeholder="Crate Code"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                aria-label="Crate Code"
              />
            </div>

            <button 
              className="modal-btn" 
              type="button" 
              onClick={addToTable}
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {!isLoading ? 'Select Crate' : 'Checking Availability...'}
            </button>
          </div> 
        </div>
      </>
    ) : (
      <>
        <div className="modal-backdrop" onClick={closeModal}></div>
        <div className="modal" role="dialog" aria-modal="true">
          {itemIsValidated ? (
            <div className="flex flex-col items-center modal-content">
              <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
                {itemCode} : {itemDescription}
              </p>

              <div className="input-container w-full">
                <label htmlFor="requested_quantity">
                  Requested Quantity 
                  <input
                    className="input-field mb-0"
                    name="requested_quantity"
                    id="requested_quantity"
                    type="text"
                    placeholder="Requested Quantity"
                    value={requestedQuantity} 
                    readOnly
                    aria-readonly="true"
                  />
                </label>
              </div>
              
              {crates.length > 1 ? (
                <>
                  <table className="min-w-full border border-gray-300 border-collapse mb-4 table-fixed">
                    <thead className="bg-gray-200">
                      <tr>
                        <th className="w-1/2 border border-gray-300 px-4 py-2 text-left">Crate</th>
                        <th className="w-1/2 border border-gray-300 px-4 py-2 text-left">Qty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {crates.map((crate, index) => (
                        <tr key={crate.crate_code} className="hover:bg-gray-50">
                          <td className="w-1/2 border border-gray-300 px-4 py-2">{crate.crate_code}</td>
                          <td className="w-1/2 border border-gray-300 px-4 py-2">
                            <div className="relative">
                              <input
                                className="bg-[#e2e2e2] p-2 rounded-md m-0 pr-12 w-full no-spinner"
                                name={`crate_qty_${index}`}
                                id={`crate_qty_${index}`}
                                type="number"
                                min={1}
                                value={crate.scanned_qty}
                                onChange={(e) => handleQuantityChange(index, e.target.value)}
                                aria-label={`Quantity for crate ${crate.crate_code}`}
                              />
                              <span className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none text-sm">
                                {crate.uom}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className='w-full flex flex-row gap-2'>
                    <button 
                      className="modal-btn" 
                      type="button" 
                      onClick={() => handleSubmitScan({scannedQuantity: 0, crates: crates, itemType: "crates", closeCrate: closeCrate})}
                    >
                      Submit Scan
                    </button>

                    <button className="modal-btn" type="button" onClick={addCrate}>
                      Add Crate
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="input-container w-full">
                    <label htmlFor="crate_code">
                      Crate Code
                      <input
                        className="input-field mb-0"
                        name="crate_code"
                        id="crate_code"
                        type="text"
                        placeholder="Crate Code"
                        value={crateCode} 
                        readOnly
                        aria-readonly="true"
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
                        min={1}
                        onChange={(e) => setScannedQuantity(parseInt(e.target.value) || 0)}
                        aria-label="Scanned Quantity"
                      />
                    </label>
                  </div>

                  <div className='w-full flex flex-row gap-2'>
                    <button 
                      className="modal-btn" 
                      type="button" 
                      onClick={() => handleSubmitScan({scannedQuantity: scannedQuantity, itemType: "crate", closeCrate: closeCrate})}
                    >
                      Submit Scan
                    </button>

                    <button className="modal-btn" type="button" onClick={addCrate}>
                      Add Crate
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (   
            <div className="flex flex-col items-center modal-content">
              <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
                {itemCode}
              </p>

              <div className="input-container w-full">
                <label htmlFor="item_barcode">
                  Scan Item 
                  <input
                    className="input-field mb-0"
                    name="item_barcode"
                    id="item_barcode"
                    type="text"
                    placeholder="Barcode"
                    value={itemBarcode}
                    onChange={(e) => setItemBarcode(e.target.value)}
                    aria-label="Item Barcode"
                  />
                </label>
              </div>

              <button className="modal-btn" type="button" onClick={handleVerifyBarcode}>
                Verify
              </button>
            </div>
          )}
        </div>
      </>
    )}
    </>
  );
}
