import { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { useAuth } from '../context/AuthContext';
import {frappeClient} from '../../utils/client';
import MaterialRequestItem from '../components/MaterialRequestItem';

export default function MaterialRequestList() {
  const { user } = useAuth();
  const [materialRequests, setMaterialRequests] = useState<any[]>([]);
 
  useEffect(() => {
    const searchParams = {user: user};

    const fetchAssignedMaterialRequests = async function () {
      const response = await frappeClient.get('pick_stream.api.get_material_request_list_view', searchParams);
    
      setMaterialRequests(response.message.data);
    };

    fetchAssignedMaterialRequests();
  }, []);
 
  return (
    <>
      <div className='matreq-list-container'>
        {materialRequests && materialRequests.map(materialRequest => {
          return <MaterialRequestItem {...materialRequest}/>
        })}
      </div>
    </>
  );
}
