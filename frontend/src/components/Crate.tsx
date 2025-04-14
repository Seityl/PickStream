import { FaBoxOpen } from "react-icons/fa";

export default function Crate({crate_code, status}: any) {
  return (
    <div className='crate'>
                
      <FaBoxOpen className='crate-icon'/>

      <div className='crate-details'>
        <p className='crate-code'>{crate_code}</p>
        <p className='crate-status'>{status}</p>
      </div>
    </div>
  )
}
