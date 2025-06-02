import {useState} from 'react';

export default function SkipItemModal({skipItem, closeModal}: any) {
  const [closeCrate, setCloseCrate] = useState(false);
  return (
    <>
    <div className="modal-backdrop" onClick={closeModal}></div>
    <div className="modal">

      <div className="flex flex-col items-center modal-content">
        <p>Are you sure you want to skip this item?</p>

        <label htmlFor="close_crate" className='flex flex-row justify-center self-start mt-1 mb-2'>
          
          <input type="checkbox" checked={closeCrate} onChange={() => setCloseCrate((prevState) => !prevState)}/>

          <p className='ml-2'>Close Crate</p>
        </label>

        <div className="flex flex-row items-center gap-x-4">
          <button className="rounded-[5px] py-2 px-4 bg-[#171717] text-white font-bold" type="submit" onClick={() => skipItem(closeCrate)}>
            Yes
          </button>
          
          <button className="rounded-[5px] py-2 px-4 bg-[#171717] text-white font-bold" type="button" onClick={closeModal}>
            No
          </button>
        </div>
      </div>
    </div>
    </>
  )
}
