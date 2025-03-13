import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { FaArrowLeft } from 'react-icons/fa6';
export default function Picking() {
  const [isHidden, setIsHidden] = useState(true);
  const [stream, setStream] = useState({
    materialRequest: 'MAT-MR-2025-01390',
  });
  const navigate = useNavigate();
  const params = useParams();

  function toggleModal() {
    setIsHidden((prevState) => {
      return !prevState;
    });
  }

  function backToMaterialRequest() {
    navigate(`/material-requests/${stream.materialRequest}`);
  }

  return (
    <main className="relative min-h-screen w-full flex flex-col">
      <header className="flex flex-row justify-between items-center px-4 py-6 mb-10 bg-gray-200">
        <button className="cursor-pointer" onClick={backToMaterialRequest}>
          <FaArrowLeft />
        </button>

        <p>MAT-MR-2025-01390</p>
      </header>

      <form className="px-4">
        {!isHidden ? (
          <div className="modal">
            <div className="modal-backdrop" onClick={toggleModal}></div>

            <div className="flex flex-col items-center modal-content">
              <p className="mb-8 rounded-[6px] bg-[#e2e2e2] p-[6px]">
                100/CASE4
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
                  />
                </label>
              </div>

              <button className="scan-btn" type="submit" onClick={toggleModal}>
                Verify Item
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
            />
          </label>
        </div>

        <button className="scan-btn" type="button" onClick={toggleModal}>
          Scan
        </button>
      </form>
    </main>
  );
}
