import {useFrappeGetCall, useFrappeAuth,} from 'frappe-react-sdk';
import {Link} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import ItemIdentifierNode from '../components/ItemIdentifierNode';

export default function IdentifierLookup() {
  const {currentUser} = useFrappeAuth();

  const { data: itemIdentifierList, mutate: refreshItemIdentifierList } = useFrappeGetCall<{ message: any }>(
    "pick_stream.api.get_item_identifier_list",
    {
      user: currentUser
    },
    undefined,
    {
      revalidateOnFocus: true
    },
    "GET"
  );
  const itemIdentifiers = itemIdentifierList?.message.data;
  return (
    <main>
       <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white'>
            <Link to={`/pick_stream/tools`}>
              <FaArrowLeft size={24}/>
            </Link>
    
            <p className='mx-auto text-xl font-semibold'>Identifier Lookup</p>
      </header>
      <div className="matreq-list-container mb-14">
        {
          itemIdentifiers ? itemIdentifiers.map((itemIdentifier: any) => {
            return <ItemIdentifierNode {...itemIdentifier}/>
          }) 
          : 
          <p className="self-center">No Data</p>
        }
      </div>
    </main>
  )
}
