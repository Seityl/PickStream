import React, {} from 'react';
import { AiFillProfile } from "react-icons/ai";
import { Link } from 'react-router';
import { MatReqItem } from '../../types';


export default function MaterialRequestItem(props: MatReqItem) {

  const {name, target_warehouse, source_warehouse, status, item_group_availability} = props;

  const statusColorMapping: Record<string, string> = {
    Open: '#1B8E2D',
    Pending: '#FFBF00'
  }; 

  const borderColor = statusColorMapping[status];

  return (
    <Link to={`/pick_stream/material-requests/${name}`}>
      <div className={`matreq-item-container border-left-[${borderColor}]`}>
        <div className='matreq-item-header'>
          <AiFillProfile/>
          <p className='matreq-item-name'>{name}</p>
          <p className='matreq-item-status'>{status}</p>
        </div>

        <p>From {source_warehouse ? source_warehouse : 'KG Warehouse - JP'} to{' '}
        {target_warehouse}</p>

        <div className='matreq-item-available-groups'>
         {item_group_availability.map((item_group: any)=> {
          return <div className={`item-group ${!item_group.available ? 'not-available' : 'available'}`}><p>{item_group.name}: {item_group.reason}</p></div>;
         })}
        </div>
      </div>
    </Link>
  )
}
