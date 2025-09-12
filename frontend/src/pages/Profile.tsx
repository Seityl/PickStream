import { useState } from 'react';
import { useLoaderData, useNavigate } from 'react-router';
import avatar from '../assets/profile-placeholder.jpg';
import { useAuth } from '../context/AuthContext';
import { getCurrentUser } from '../../utils/auth';
import { getUserProfile } from '../../utils/api';

function Profile() {
  const userProfile = useLoaderData() as any;
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [error, setError] = useState('');

  async function handleSignOut() {
    setIsSigningOut(true);
    setError('');
    
    try {
      await signOut();
      navigate('/login');
    } catch (e) {
      setError('Unable to sign out. Please try again.');
      setIsSigningOut(false);
    }
  }

  const profileData = userProfile || {};
  const userInitials = profileData.full_name 
    ? profileData.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase()
    : (user ? user[0].toUpperCase() : 'U');

  return (
    <main className='flex flex-col bg-gray-50'>
      {/* Header Section */}
      <div className="bg-white shadow-sm">
        <div className='max-w-md mx-auto p-6'>
          <div className='flex flex-col items-center text-center'>
            {/* Profile Image with Fallback */}
            <div className='w-24 h-24 mb-4 relative group'>
              {profileData.user_image ? (
                <img 
                  className='object-cover h-full w-full rounded-full border-2 border-gray-100' 
                  src={profileData.user_image} 
                  alt={`${profileData.full_name || 'User'}'s profile`}
                  onError={(e) => {
                    // Fallback to avatar if user image fails to load
                    e.currentTarget.src = avatar;
                  }}
                />
              ) : (
                <div className='w-full h-full rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-xl font-semibold border-2 border-gray-100'>
                  {userInitials}
                </div>
              )}
              
              {/* Online Status Indicator */}
              <div className="absolute bottom-1 right-1 w-6 h-6 bg-green-400 rounded-full border-2 border-white flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full"></div>
              </div>
            </div>
            
            {/* User Information */}
            <h1 className='text-2xl font-bold text-gray-900 mb-1'>
              {profileData.full_name || 'User Name'}
            </h1>
            
            <p className='text-sm text-gray-600 mb-2'>
              {profileData.email || user || 'user@example.com'}
            </p>
            
            {/* User Role/Department if available */}
            {profileData.designation && (
              <span className='inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800'>
                {profileData.designation}
              </span>
            )}
          </div>
        </div>
      </div>
      
      {/* Profile Details Section */}
      <div className="flex-1 max-w-md mx-auto w-full px-4">
        {/* User Details Card */}
        <div className="mt-6 bg-white rounded-lg shadow-sm">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Profile Information</h2>
          </div>
          
          <div className="p-4 space-y-4">
            {/* Full Name */}
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500">Full Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{profileData.full_name || 'Not provided'}</dd>
              </div>
            </div>
            
            {/* Email */}
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500">Email</dt>
                <dd className="mt-1 text-sm text-gray-900">{profileData.email || user || 'Not provided'}</dd>
              </div>
            </div>
            
            {/* Phone if available */}
            {profileData.phone && (
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-gray-500">Phone</dt>
                  <dd className="mt-1 text-sm text-gray-900">{profileData.phone}</dd>
                </div>
              </div>
            )}
            
            {/* Department/Company if available */}
            {(profileData.department || profileData.company) && (
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-gray-500">
                    {profileData.department ? 'Department' : 'Company'}
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {profileData.department || profileData.company}
                  </dd>
                </div>
              </div>
            )}
            
            {/* Branch if available */}
            {profileData.branch && (
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-gray-500">Branch</dt>
                  <dd className="mt-1 text-sm text-gray-900">{profileData.branch}</dd>
                </div>
              </div>
            )}
            
            {/* Employee ID if available */}
            {profileData.employee && (
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-gray-500">Employee ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">
                    {profileData.employee}
                  </dd>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Actions Section */}
        <div className="mt-6 mb-8">
          {/* Sign Out Section */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            {error && (
              <div className="p-4 bg-red-50 border-l-4 border-red-400">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
            
            <button
              className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium py-3 px-4 rounded-lg transition-all duration-200 disabled:cursor-not-allowed focus:outline-none focus:ring-4 focus:ring-red-200 active:transform active:scale-98 flex items-center justify-center gap-3"
              type="button"
              onClick={handleSignOut}
              disabled={isSigningOut}
            >
              {isSigningOut ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Signing out...</span>
                </>
              ) : (
                <>
                  <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H3" />
                  </svg>
                  <span>Sign Out</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

export default Profile;

export async function profileLoader() {
  try {
    const user = await getCurrentUser();
    if (!user) {
      throw new Error('No authenticated user found');
    }
    return await getUserProfile(user);
  } catch (error) {
    console.error('Profile loader error:', error);
    // Return empty profile data to prevent app crash
    return { 
      message: { 
        status: 500, 
        data: {} 
      } 
    };
  }
}