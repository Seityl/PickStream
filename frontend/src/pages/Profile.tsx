import { useLoaderData } from 'react-router';
import avatar from '../assets/profile-placeholder.jpg';
import { useAuth } from '../context/AuthContext';
import { getUserProfile } from '../../utils/api';

function Profile() {
  const userProfile = useLoaderData();
  const { user, signOut } = useAuth();

  async function handleSignOut() {
    try {
      await signOut();
    } catch (e) {
      alert('Something went wrong.');
    }
  }

  return (
    <main className='min-h-screen flex flex-col px-4 pt-20'>

      <div className='w-[180px] h-[180px] self-center mb-5'>
        <img className='object-cover h-full w-full rounded-[50%]' src={avatar} alt={user!}/>
      </div>
      
      <p className='text-3xl font-semibold self-center mb-4'>Walter Perkins</p>

      <p className='font-semibold self-center mb-5 py-2 px-4 bg-[#f3f3f3] rounded-[20px]'>wperkins@jollys.local</p>
      
      <div className='w-full bg-[#f3f3f3] rounded-[6px] p-4 mb-10'>
        <div className='flex flex-row justify-between'>
          <p>Points Earned</p>
          <p>5000</p>
        </div>

        <div className='flex flex-row justify-between'>
          <p>Branch</p>
          <p>King George</p>
        </div>

        <div className='flex flex-row justify-between'>
          <p>Points Earned</p>
          <p>5000</p>
        </div>

        <div className='flex flex-row justify-between'>
          <p>Points Earned</p>
          <p>5000</p>
        </div>

        <div className='flex flex-row justify-between'>
          <p>Points Earned</p>
          <p>5000</p>
        </div>
      </div>

      <button
        className="bg-red-700 text-white tracking-wide uppercase font-bold cursor-pointer rounded-[6px] py-2 shadow-md transition-transform active:scale-95"
        type="button"
        onClick={signOut}
      >
        Sign Out
      </button>
    </main>
  );
}

export default Profile;


export async function profileLoader() {
  const user = localStorage.getItem('user');
  return await getUserProfile(user!);
}
