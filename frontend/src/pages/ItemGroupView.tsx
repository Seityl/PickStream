import { useState, useEffect } from 'react';
import {useParams, Link, useLocation, useNavigate} from 'react-router';
import { useAuth } from '../context/AuthContext';
import {frappeClient} from '../../utils/client';
import Crate from '../components/Crate';
import { FaPlus } from "react-icons/fa";

type crate = {
  crate_code: string;
  item_group: string;
  status: string;
}

// export async function clientLoader() {
//   const res = await fetch(`/api/products/${params.pid}`);
//   const product = await res.json();
//   return product;
// }

export default function ItemGroupView(props: any) {
  const {itemGroup} = props;
  const {user} = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [viewData, setViewData] = useState(null);
  const [isHidden, setIsHidden] = useState(true);
  const [crateCode, setCrateCode] = useState('');
  const [crates, setCrates] = useState<crate[]>([]);
  const [isValid, setIsValid] = useState(false);
  const queryParams = useParams();
  const materialRequest = queryParams.material_request;
  
  
  useEffect(() => {
    const fetchItemGroupViewData = async function () {
      const queryParams = {
        user: user,
        mr_name: materialRequest,
        item_group: itemGroup,
      };
  
      const response = await frappeClient.get('pick_stream.api.get_material_request_item_group_view', queryParams);
      
      if (response.message.data.in_progress) {
        setCrateCode(response.message.data.crate_code);

        navigate(`/pick_stream/picking/${materialRequest}?item_group=${itemGroup}&crate_code=${crateCode}`);
      } else {
        

        setViewData(response.message.data);
        setCrates(response.message.data.crates);
      }
    }
    fetchItemGroupViewData();
  }, [itemGroup, location])

  useEffect(() => {
    if (crateCode && isValid) {
      navigate(`/pick_stream/picking/${materialRequest}?item_group=${itemGroup}&crate_code=${crateCode}`);
    }

  }, [crateCode, isValid])

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
    console.log(response.message.data);
    setIsValid(response.message.data);
  }

  return ( 
    <div className='mt-10'>
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
                      onChange={(e) => setCrateCode(e.target.value)}
                    />
                </div>

                <button className="scan-btn" type="submit" onClick={() => validateCrate()}>
                    Select Crate
                </button>
              </div>
            </div>
        </>
        :  
        ''
      }
     
      <p>{itemGroup}</p>

      <p>Crates</p>
      <button className='create-crate-btn' onClick={toggleModal}><FaPlus /></button>
      <div className='mt-10'>
        <ul className='flex flex-col gap-y-3'>
          {crates.length > 0 && crates.map((crate, index) => {
            return <li key={index}><Crate /></li>
          })}
        </ul>
      </div>
    </div>
  );
}
