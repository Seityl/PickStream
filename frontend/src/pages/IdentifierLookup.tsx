import {useLoaderData, Link} from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import { getCurrentUser } from '../../utils/auth';
import ItemIdentifierNode from '../components/ItemIdentifierNode';
import {getItemIdentifierList} from '../../utils/api';

function IdentifierLookup() {
  const itemIdentifiers = useLoaderData();
  console.log(itemIdentifiers);

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

export default IdentifierLookup;

export async function IdentifierLookupLoader(/*{params}: LoaderFunctionArgs*/) {
  const user = await getCurrentUser();
  const crateTransitDetails = await getItemIdentifierList(user);
  return crateTransitDetails;
}
