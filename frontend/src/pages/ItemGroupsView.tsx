import {useParams, Link, useNavigate, useLoaderData, LoaderFunctionArgs} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import { getItemGroups } from '../../utils/api';

type MaterialRequest = {
  mr_name: string;
  source_warehouse: string | null;
  target_warehouse: string;
  item_group_availability: itemGroup[]
};

type itemGroup = {
  name: string;
  available: boolean;
}

function ItemGroupsView() {
  const navigate = useNavigate();
  const viewData: MaterialRequest | null = useLoaderData();
  const params = useParams();
  const materialRequest = params.material_request;

  return (
    <main>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() => navigate('/pick_stream/material-requests')}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{materialRequest}</p>
      </header>
      
      <div className='px-4 mt-10'>
        <div className='flex flex-col gap-4'>
          {viewData?.item_group_availability.map(itemGroup => {
            return (
              <Link to={`/pick_stream/material-requests/${materialRequest}/${encodeURIComponent(itemGroup.name)}`} className='item-group-btn'>{itemGroup.name}</Link>
            )
          })}
        </div>
      </div>
    </main>
  );
}

export default ItemGroupsView;

export async function itemGroupsLoader({params}: LoaderFunctionArgs) {
  const user = localStorage.getItem('user');
  const { material_request } = params;
  return await getItemGroups(user!, material_request!);
}
