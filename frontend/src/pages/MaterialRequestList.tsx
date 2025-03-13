import { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { useAuth } from '../context/AuthContext';
import frappeClient from '../../utils/client';
import { FaFileLines } from 'react-icons/fa6';

export default function MaterialRequestList() {
  const { user } = useAuth();
  const [materialRequests, setMaterialRequests] = useState<any[]>([]);
  const call = frappeClient.call();
  useEffect(() => {
    const searchParams = {user: user};

    const fetchAssignedMaterialRequests = async function () {
      const response = await call.get('pick_stream.api.get_material_request_list_view', searchParams);
    
      setMaterialRequests(response.message.data);
    };

    fetchAssignedMaterialRequests();
  }, []);
 
  return (
    <div>
      {materialRequests && materialRequests.map(materialRequest => {
        return (
          <Link to={`/pick_stream/material-requests/${materialRequest.name}`}>
            <div className="p-2 w-full">
              <div className="bg-gray-100 rounded flex p-4 h-full items-center">
                  <FaFileLines/>
                  <span className="font-medium">{materialRequest.name}</span>
              </div>
            </div>
          </Link>
        )
      })}
    </div>
  );
}
