import { AiFillProfile } from "react-icons/ai";
import { Link } from 'react-router';


export default function ItemIdentifierNode(props: any) {

  const {name, item_type, item_code, user, to_warehouse, from_warehouse} = props;

  const statusColorMapping: Record<string, string> = {
    Open: '#1B8E2D',
    Pending: '#FFBF00'
  }; 

  const borderColor = statusColorMapping[status];

  return (
    <Link to={`/pick_stream/tools/item-lookup/${name}`}>
      <div className={`identifier-node-container border-left-[${borderColor}]`}>
        <div className='identifier-header'>
          <AiFillProfile/>
          <p className='identifier-item-code'>{item_code}</p>
          <p className='identifier-item-type'>{item_type}</p>
        </div>

        <p>From {from_warehouse ? from_warehouse : 'KG Warehouse - JP'} to{' '}
        {to_warehouse}</p>

        <div className='identifier-associated-user'>
          <p>By {user}</p>
        </div>
      </div>
    </Link>
  )
}
