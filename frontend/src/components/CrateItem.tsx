import React, {} from 'react';
import { AiFillProfile } from "react-icons/ai";
// import { Link } from 'react-router';
// import { MatReqItem } from '../../types';


export default function CratetItem(props: any) {

  const {crate_code} = props;

  

  return (
     <div className='crate-item-container'>
      <p>{crate_code}</p>
    </div>
  )
}
