import { useState, useEffect } from 'react';
import {useParams, useNavigate, useLoaderData, LoaderFunctionArgs, redirect} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import {frappeClient} from '../../utils/client';
import {getItemGroupData} from '../../utils/api';

import Crate from '../components/Crate';
import { FaPlus } from "react-icons/fa";

type crate = {
  crate_code: string;
  item_group: string;
  status: string;
}

function ItemGroupView() {
  const navigate = useNavigate();
  const viewData = useLoaderData();
  const [isHidden, setIsHidden] = useState(true);
  const [crateCode, setCrateCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isValid, setIsValid] = useState(false);
  const routeParams = useParams();
  const materialRequest = routeParams.material_request;
  const itemGroup = decodeURIComponent(routeParams.item_group!);

  useEffect(() => {
    if (crateCode && isValid) {
      redirect(`/pick_stream/picking?mr_name=${materialRequest}&item_group=${itemGroup}&crate_code=${crateCode}`);
    }

  }, [isValid])

  function toggleModal() {
    setIsHidden((prevState) => {
      return !prevState;
    });
  }

  async function validateCrate() {
    const params = {
      crate_code: crateCode
    };

    const response = await frappeClient.get('pick_stream.api.validate_crate', params);
    setIsValid(response.message.data);
  }

  return ( 
    <main>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white relative'>
        <button onClick={() =>navigate(`/pick_stream/material-requests/${materialRequest}`)}>
          <FaArrowLeft size={24}/>
        </button>

        <p className='mx-auto text-xl font-semibold'>{itemGroup}</p>
      </header>
      <div className='px-4 mt-10'>
        {!isHidden ? 
          <>
            <div className="modal-backdrop" onClick={toggleModal}></div>

            <div className="modal">
              <div className="flex flex-col items-center modal-content">
                  <p className=''>Enter Crate Code</p>

                  <div className="input-container w-full">
                      <input
                        className="input-field mb-0 w-full"
                        name="crate_code"
                        id="crate_code"
                        type="text"
                        placeholder="Crate Code"
                        value={crateCode}
                        onChange={(e) => {setCrateCode(e.target.value);}}
                      />
                  </div>

                  <button className="modal-btn" type="submit" onClick={() => validateCrate()}>
                  {error ? error : !isLoading ? 'Select Crate' : 'Checking Availability...'}
                  </button>
                </div>
              </div>
          </>
          :  
          ''
        }

        <p className='text-2xl font-bold mb-10'>Crates</p>
        <button className='create-crate-btn' onClick={toggleModal}><FaPlus /></button>
        <div className='mt-10'>
          <ul className='flex flex-col gap-y-3'>
            {viewData.crates.length > 0 && viewData.crates.map((crate: crate, index: number) => {
              return <li key={index}><Crate {...crate} /></li>
            })}
            {viewData.crates.length === 0 && 
              (
                <div>
                  <p className='text-center'>This Item Group Has No Crates.</p>
                </div>
              )
            }
          </ul>
        </div>
      </div>
    </main>
  );
}

export default ItemGroupView;

export async function itemGroupLoader({params}: LoaderFunctionArgs){
  const user = localStorage.getItem('user');
  const {material_request, item_group} = params;

  try {
    const data = await getItemGroupData(user!, material_request!, decodeURIComponent(item_group!));
  
    if (data.in_progress) {
      const crate_code = data.crate_code;
  
      return redirect(`/pick_stream/picking?mr_name=${material_request}&item_group=${item_group}&crate_code=${crate_code}`);
    } else {
      return data;
    }
  } catch(err) {
    console.log('error: ', err);
  }

}
