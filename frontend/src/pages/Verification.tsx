import React from 'react';
import { Link, useLoaderData } from 'react-router';
import { FaArrowLeft } from "react-icons/fa";
import { getVerificationListView } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';
import ListItem from '../components/ListItem';

type Identifier = {
  identifier_code: string;
  source_warehouse: string;
  target_warehouse: string
}

type Crate = {
  crate_code: string;
  source_warehouse: string;
  target_warehouse: string
}

type VerificationListType = {
  crate_details: Crate[];
  identifier_details: Identifier[];
};

export async function verificationLoader() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Response("Not Logged In", { status: 401 });
  }
  const verificationList = await getVerificationListView(user);
  return { verificationList };
}

function VerificationList() {
  const { verificationList } = useLoaderData() as { verificationList: VerificationListType };

  const groupedItems = [...verificationList.crate_details, ...verificationList.identifier_details].reduce((acc, item) => {
    const key = `${item.source_warehouse} -> ${item.target_warehouse}`;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {} as Record<string, (Crate | Identifier)[]>);


  return (
    <main className='min-h-screen'>
      <header className='flex flex-row items-center px-4 py-6 bg-[#171717] text-white'>
        <Link to={`/pick_stream/`}>
          <FaArrowLeft size={24}/>
        </Link>
        <p className='mx-auto text-xl font-semibold'>Awaiting Verification</p>
      </header>
      <div className='matreq-list-container mb-15'>
        {Object.keys(groupedItems).length === 0 ? (
          <p className="p-4 text-center">No items to verify.</p>
        ) : (
          Object.entries(groupedItems).map(([group, items]) => (
            <div key={group}>
              <h2 className="text-md font-bold p-4">{group}</h2>
              <div className="flex flex-col gap-y-2 px-4">
                {items.map((item) => {
                  const isCrate = 'crate_code' in item;
                  const code = isCrate ? item.crate_code : item.identifier_code;
                  const type = isCrate ? 'crate' : 'item';
                  const linkTo = `/pick_stream/verification/${type}/${code}`;

                  return (
                    <Link to={linkTo} key={code}>
                      <ListItem code={code} type={type} />
                    </Link>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </main>
  );
}

export default VerificationList;
