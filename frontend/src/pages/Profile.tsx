import React from 'react';
import { useLoaderData, useNavigate } from 'react-router';
import avatar from '../assets/profile-placeholder.jpg';
import { useAuth } from '../context/AuthContext';
import { getCurrentUser } from '../../utils/auth';
import { getUserProfile } from '../../utils/api';

function Profile() {
  const userProfile = useLoaderData() as any;
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    try {
      await signOut();
      navigate('/login');
    } catch (e) {
      alert('Something went wrong.');
    }
  }

  return (
    <main className='min-h-screen flex flex-col bg-gray-50'>
      <div className="bg-white p-6 shadow-sm">
        <div className='flex flex-col items-center'>
          <div className='w-24 h-24 self-center mb-4'>
            <img className='object-cover h-full w-full rounded-full' src={avatar} alt={user || 'User'}/>
          </div>
          
          <p className='text-2xl font-bold text-gray-800 self-center mb-1'>{userProfile?.message?.full_name || 'User Name'}</p>

          <p className='text-sm text-gray-500 self-center'>{userProfile?.message?.email || user || 'user@example.com'}</p>
        </div>
      </div>
      
      <div className="mt-6">
        <ul className="bg-white shadow-sm">
          <li>
            <button
              className="w-full text-left p-4 text-red-500 font-medium flex justify-between items-center transition-colors hover:bg-gray-50"
              type="button"
              onClick={handleSignOut}
            >
              <span>Sign Out</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H3" />
              </svg>
            </button>
          </li>
        </ul>
      </div>
    </main>
  );
}

export default Profile;

export async function profileLoader() {
  const user = await getCurrentUser();
  return await getUserProfile(user!);
}
