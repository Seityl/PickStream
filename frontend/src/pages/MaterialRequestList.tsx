import { useLoaderData, Link } from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import MaterialRequestItem from '../components/MaterialRequestItem';
import {getMaterialRequests} from '../../utils/api';
import { MatReqItem } from '../../types';

function MaterialRequestList() {
  const materialRequests = useLoaderData();
  console.log(materialRequests);
  return (
    <main className='min-h-screen'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white'>
            <Link to={`/pick_stream/`}>
              <FaArrowLeft size={24}/>
            </Link>
    
            <p className='mx-auto text-xl font-semibold'>Material Requests</p>
      </header>
      <div className='matreq-list-container'>
        {materialRequests && materialRequests.map((materialRequest: MatReqItem) => {
          return <MaterialRequestItem {...materialRequest}/>
        })}
      </div>
      
      {materialRequests.length === 0 &&  (<div className=" flex h-full justify-center items-center">
        <div className='w-100 text-center'>
          <p className='text-center'>You have no assigned Material Requests.</p>
        </div>
      </div>)}
    </main>
  );
}

export default MaterialRequestList;


export async function materialRequestLoader() {
  const user = localStorage.getItem('user');
  console.log('material request loader - ', user);
  return await getMaterialRequests(user!);
}
