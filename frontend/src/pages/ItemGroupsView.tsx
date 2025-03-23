import React, { useState, useEffect } from 'react';
import {useParams, Link, useSearchParams} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import { useAuth } from '../context/AuthContext';
import {frappeClient} from '../../utils/client';
import ItemGroupView from './ItemGroupView';

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

export default function ItemGroupsView() {
  const {user} = useAuth();
  const [viewData, setViewData] = useState<MaterialRequest | null>(null);
  const params = useParams();
  const [searchParams] = useSearchParams();
  const itemGroup = searchParams.get('item_group');
  const materialRequest = params.material_request;

  useEffect(() => {
    const queryParams = {
      user: user,
      mr_name: materialRequest
    }

    const fetchItemGroupsViewData = async function() {
      const response = await frappeClient.get('pick_stream.api.get_material_request_available_item_groups_view', queryParams);

      setViewData(response.message.data);
    }

    fetchItemGroupsViewData();
  }, []);

  
  return (
    <main>
      <header className='flex flex-row justify-between items-center px-4 py-4'>
            <Link to={`/pick_stream/material-requests${itemGroup ? `/${materialRequest}`:''}`}>
              <FaArrowLeft />
            </Link>
    
            <p>{materialRequest}</p>
      </header>
      
      <div className='px-4 mt-10'>

        { itemGroup ?
            <ItemGroupView itemGroup={itemGroup}/>
          :
            <div className='flex flex-col gap-4'>
              {viewData?.item_group_availability.map(itemGroup => {
                return (
                  <Link to={`/pick_stream/material-requests/${materialRequest}?item_group=${(itemGroup.name)}`} className='item-group-btn'>{itemGroup.name}</Link>
                )
              })}
            </div>
        }
      </div>
    </main>
  );
}
