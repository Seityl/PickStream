import { useState, useCallback } from 'react';

type SkipItemModalProps = {
  skipItem: (closeCrate: boolean) => Promise<void>;
  closeModal: () => void;
  isLoading?: boolean; // Add isLoading prop
};

export default function SkipItemModal({ skipItem, closeModal }: SkipItemModalProps) {
  const [closeCrate, setCloseCrate] = useState(false);
  
  const handleSkipItem = useCallback(() => {
    skipItem(closeCrate);
  }, [skipItem, closeCrate]);

  return (
    <>
    <div className="modal-backdrop" onClick={closeModal}></div>
    <div className="modal" role="dialog" aria-modal="true">
      <div className="flex flex-col items-center modal-content">
        <p>Are you sure you want to skip this item?</p>

        <label htmlFor="close_crate" className='flex flex-row justify-center self-start mt-1 mb-2'>
          <input 
            type="checkbox" 
            id="close_crate"
            checked={closeCrate} 
            onChange={() => setCloseCrate((prevState) => !prevState)}
            aria-label="Close Crate"
          />
          <p className='ml-2'>Close Crate</p>
        </label>

        <div className="flex flex-row items-center gap-x-4">
          <button 
            className="rounded-[5px] py-2 px-4 bg-[#171717] text-white font-bold" 
            type="button" 
            onClick={handleSkipItem}
          >
            Yes
          </button>
          
          <button 
            className="rounded-[5px] py-2 px-4 bg-[#171717] text-white font-bold" 
            type="button" 
            onClick={closeModal}
          >
            No
          </button>
        </div>
      </div>
    </div>
    </>
  );
}
