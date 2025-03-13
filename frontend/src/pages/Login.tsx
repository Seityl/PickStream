import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const { isAuthenticated, signIn, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (isAuthenticated) {
      navigate(/*location.state?.from?.pathname ||*/ '/pick_stream', { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  async function handleSubmit(e: React.FormEvent) {
    try {
      e.preventDefault();

      if (!email) {
        setError('Email field cannot be left blank.');
      }

      if (!password) {
        setError('Password field cannot be left blank.');
      }

      if (!email && !password) {
        setError('Fields cannot be left blank.');
      }

      const result = await signIn(email, password);
    } catch (e) {
      setError('Invalid login. Please try again.');
    }
  }
  return (
    <main className="min-h-screen px-6 pt-10">
      <img className="block object-contain mb-10" src="./icons/logo.svg" alt="Logo" />
      <form className="flex flex-col gap-y-4" onSubmit={handleSubmit}>
        <input
          className="bg-[#e2e2e2] p-2 rounded-[6px]"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="bg-[#e2e2e2] p-2 rounded-[6px]"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          className="cursor-pointer bg-[#171717] text-white py-2 rounded-[6px]"
          type="submit"
        >
          {error ? error : !isLoading ? 'Login' : 'Verifying...'}
        </button>
      </form>
    </main>
  );
}
