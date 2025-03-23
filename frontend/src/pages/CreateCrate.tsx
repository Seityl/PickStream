import {useState, useEffect} from 'react';
import { useSearchParams } from 'react-router';
import { useAuth } from '../context/AuthContext';
import {frappeClient} from '../../utils/client';

type MaterialRequest = {
  name: string;
  source_warehouse: string | null;
  target_warehouse: string;
  status: string;
  item_group_availability: []
};

export default function CreateCrate() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [itemGroup, setItemGroup] = useState('');
  const [crateCode, setCrateCode] = useState('');
  const [crateError, setCrateError] = useState('');
  const [materialRequestData, setMaterialRequestData] = useState<MaterialRequest | null>(null);
  const [crateIsValid, setCrateIsValid] = useState(false);
  const materialRequestName = searchParams.get('material_request');
  const { user } = useAuth();

  async function validateCrate(crateCode: string) {
    try {
      const data = {crate_code: crateCode};

      const response = await frappeClient.get('pick_stream.api.validate_crate', data);
      console.log(response.data.message);
      setCrateIsValid(response.data.message);
    }
    catch(err: any) {
      if (err.httpStatus === 404) {
        setCrateError('Crate does not exist.')
      }
    }
  }
  useEffect(() => {
    const data = {user: user, mr_name: materialRequestName};

    const fetchMaterialRequestDetails = async function () {
      const response = await frappeClient.get('pick_stream.api.get_material_request_detail_view', data);
    
      setMaterialRequestData(response.message.data);
    };

    fetchMaterialRequestDetails();
  }, []);
  return (
    <main className='px-4 min-h-screen'>
       <div className='w-full mt-10 h-full flex flex-col justify-center items-center'>

       <div className='input-container w-full'>
          <label htmlFor="item-group">
            Crate Code
            <select
               className='input-field w-full'
               id="item-group"
               name='item_group'
               onChange={(e) => setItemGroup(e.target.value)} 
              //  value={crateCode}
            >
             <option value="">Select Item Group</option>
             
            </select>
          </label>
        </div>

        <button onClick={() => validateCrate(crateCode)}>Select Crate</button>
        {crateError ? <p>Crate is in use, Select another</p> : ''}

        <div className='input-container w-full'>
          <label htmlFor="crate-code">
            Crate Code
            <input 
              className='input-field w-full'
              type="text"
              id="crate-code"
              name='crate_code'
              placeholder='Enter Crate Code'
              onChange={(e) => setCrateCode(e.target.value)} 
              value={crateCode}
            />
          </label>
        </div>

        <button onClick={() => validateCrate(crateCode)}>Select Crate</button>
        {crateError ? <p>Crate is in use, Select another</p> : ''}
      </div>
    </main>
  );
}
