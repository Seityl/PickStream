import { FaBoxOpen } from "react-icons/fa";

export default function Crate() {
  return (
    <div className='crate'>
                
      <FaBoxOpen className='crate-icon'/>

      <div className='crate-details'>
        <p className='crate-name'>CY102</p>
        <p className='crate-status'>Open</p>
      </div>
    </div>
  )
}
