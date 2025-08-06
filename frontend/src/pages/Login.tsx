import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router';
import { motion } from 'motion/react';
import logo from '../assets/placeholder-png.png';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';

const imageVariants = {
  hidden: { y: -50, opacity: 0 },
  show: {
    y: 0,
    opacity: 1,
    transition: { type: 'tween', duration: 0.35, ease: 'easeOut' },
  },
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.08,
    },
  },
};

const inputVariants = {
  hidden: { y: 40, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { type: 'tween', duration: 0.32, ease: 'easeOut' } },
};

const buttonVariants = {
  hidden: { y: 40, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { type: 'tween', duration: 0.28, ease: 'easeOut' } },
};

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { user, signIn, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isLoading && user) {
      navigate('/pick_stream', { replace: true });
    }
  }, [user, isLoading, navigate]);

  const isButtonDisabled = isSubmitting || !email.trim() || !password.trim();

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!email.trim() || !password.trim()) {
      toast.error('Please fill in both email and password.');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const result = await signIn(email, password);
      if (result.error) {
        toast.error(result.msg || 'Login failed');
      } else {
        toast.success('Login successful!');
        navigate('/pick_stream', { replace: true });
      }
    } catch (err: any) {
      toast.error('Login failed');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="px-4 pt-20">
      <motion.img
        variants={imageVariants}
        initial="hidden"
        animate="show"
        className="block object-contain"
        src={logo}
        alt="Logo"
      />
      <form className="flex flex-col gap-y-4 mt-20" onSubmit={handleSubmit}>
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="flex flex-col space-y-4"
        >
          <motion.input
            variants={inputVariants}
            className="bg-[#e2e2e2] p-4 rounded-[6px]"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isSubmitting}
            autoComplete="username"
          />
          <motion.input
            variants={inputVariants}
            className="bg-[#e2e2e2] p-4 rounded-[6px]"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isSubmitting}
            autoComplete="current-password"
          />
          <motion.button
            variants={buttonVariants}
            className={`text-lg font-bold py-4 rounded-[6px] shadow-md transition-transform active:scale-95 \
              ${isButtonDisabled
                ? 'bg-gray-500 text-gray-300 cursor-not-allowed pointer-events-none'
                : 'bg-[#171717] text-white cursor-pointer'}`}
            type="submit"
            disabled={isButtonDisabled}
          >
            {!isSubmitting ? 'Login' : 'Verifying...'}
          </motion.button>
        </motion.div>
      </form>
    </main>
  );
}
