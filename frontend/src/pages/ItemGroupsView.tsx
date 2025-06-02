import {useParams, Link, useNavigate, useLoaderData, LoaderFunctionArgs} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import { getItemGroups } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

type MaterialRequest = {
  mr_name: string;
  source_warehouse: string | null;
  target_warehouse: string;
  item_group_availability: itemGroup[]
};

type itemGroup = {
  name: string;
  reason: string;
  available: boolean;
  item_count: {
    completed: number;
    total: number;
  }
  crates: [];
}

function ItemGroupsView() {
  const navigate = useNavigate();
  const viewData: MaterialRequest | null = useLoaderData();
  const params = useParams();
  const materialRequest = params.material_request;
  console.log(viewData);
  return (
    <main>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <Link to={`/pick_stream/material-requests`}>
          <FaArrowLeft size={24}/>
        </Link>

        <p className='mx-auto text-xl font-semibold'>{viewData?.target_warehouse}</p>
      </header>
      
      <div className='px-4 mt-10'>
        <div className='flex flex-col gap-4'>
          {viewData?.item_group_availability.map(itemGroup => {
            if (itemGroup.reason !== "Completed") {
              return (
                <Link to={`/pick_stream/picking?mr_name=${materialRequest}&item_group=${itemGroup.name}`} className='item-group-btn flex flex-col'>
                  <div className='flex flex-row items-center justify-between'>
                    <p>{itemGroup.name}</p> 
                    <p>{itemGroup.item_count.completed}/{itemGroup.item_count.total}</p>
                  </div>
                
                  {itemGroup.crates.length > 0 && <div className='flex flex-row flex-wrap gap-2 mt-2 m-x-0'>
                    {itemGroup.crates.map((crate: any) => {
                      return (
                        <div className='crate-badge text-[12px]' key={crate.crate_code}><p>{crate.crate_code}: {crate.status}</p></div>
                      )})
                    } 
                  </div>}
                </Link>
              )
            } else {
              return (
                <p className='item-group-btn__disabled flex flex-row items-center justify-between'>
                  <p>{itemGroup.name}</p> 
                  <p>{itemGroup.reason}</p>
                </p>
              )
            }
          })}
        </div>
      </div>
    </main>
  );
}

export default ItemGroupsView;

export async function itemGroupsLoader({params}: LoaderFunctionArgs) {
  const user = await getCurrentUser();
  const { material_request } = params;
  return await getItemGroups(user!, material_request!);
}
