import { useLoaderData, Link } from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import CrateItem from '../components/CrateItem';
// import {getVerificationCrateList} from '../../utils/api';
import {getCurrentUser} from '../../utils/auth';

function VerificationList() {
  // const crateList = useLoaderData();
  // console.log(crateList);

  return (
    <main className='min-h-screen'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white'>
            <Link to={`/pick_stream/`}>
              <FaArrowLeft size={24}/>
            </Link>
    
            <p className='mx-auto text-xl font-semibold'>Awaiting Verification</p>
      </header>
      <div className='matreq-list-container mb-15'>
        {/* {crateList && crateList.map((crate: any) => {
          return <CrateItem {...crate}/>
        })} */}
        <CrateItem crate_code="CRATE-001" from_warehouse="Warehouse A" to_warehouse="Warehouse B" status="Pending Verification" />
        <CrateItem crate_code="CRATE-002" from_warehouse="Warehouse C" to_warehouse="Warehouse D" status="Pending Verification" />
        <CrateItem crate_code="CRATE-003" from_warehouse="Warehouse E" to_warehouse="Warehouse F" status="Pending Verification" /> 
        <CrateItem crate_code="CRATE-004" from_warehouse="Warehouse G" to_warehouse="Warehouse H" status="Pending Verification" />
      </div>
      
      {/* {crateList.length === 0 &&  (<div className=" flex h-full justify-center items-center">
        <div className='w-100 text-center'>
          <p className='text-center'>You have no Crates assigned for Verification.</p>
        </div>
      </div>)} */}
    </main>
  );
}

export default VerificationList;


// export async function VerificationLoader() {
//   const user = await getCurrentUser();
//   console.log('verification loader - ', user);
//   const verificationCrateList = await getVerificationCrateList(user!);
//   console.log('verification crate list -', verificationCrateList);
//   return verificationCrateList
//   // return await getMaterialRequests(user!);
// }
