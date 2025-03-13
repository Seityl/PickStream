import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Profile() {
  const { signOut } = useAuth();

  async function handleSignOut() {
    try {
      await signOut();
    } catch (e) {
      alert('Something went wrong.');
    }
  }

  return (
    <section>
      <button
        className="bg-red-100 text-xl cursor-pointer"
        type="button"
        onClick={signOut}
      >
        Log out
      </button>
    </section>
  );
}
