import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router';
import { motion } from 'motion/react';
import logo from '../assets/placeholder-png.png';
import { useFrappeAuth } from 'frappe-react-sdk';
import { toast } from 'react-toastify';

const imageVariants = {
  hidden: {y: -50, opacity: 0},
  show: {
    y: 0,
    opacity: 1,
    transition: { type: "tween", duration: 0.4, ease: 'easeInOut'}
  }
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2, 
    },
  },
};

const inputVariants = {
  hidden: { y: 50, opacity: 0 },
  show: { y: 0, opacity: 1, transition: {type: "tween", duration: 0.5, ease: 'easeInOut' } },
};

const buttonVariants = {
  hidden: { y: 50, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { type: "tween", duration: 0.4, ease: 'easeInOut'} },
};

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const {currentUser, login, error} = useFrappeAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  // if (currentUser) {
  //   navigate('/pick_stream', { replace: true });
  // }
 

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    setIsSubmitting(true);

    try {
      if (!email) {
        setErrorMessage('Email field cannot be left blank.');
      }

      if (!password) {
        setErrorMessage('Password field cannot be left blank.');
      }

      if (!email && !password) {
        setErrorMessage('Fields cannot be left blank.');
      }

      const result = await login({username: email, password: String.raw`${password}`});

      navigate('/pick_stream', { replace: true });
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Invalid Login");
      toast(err instanceof Error ? err.message : "Invalid Login", {
        position: "bottom-right",
        autoClose: 5000,
        hideProgressBar: false,
        closeOnClick: true, 
        rtl: false,
        theme: "dark",
        //transition={Bounce}
      })
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="px-4 pt-20">
      <motion.img variants={imageVariants} className="block object-contain" src={logo} alt="Logo" />
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
        />
        <motion.input
        variants={inputVariants}
          className="bg-[#e2e2e2] p-4 rounded-[6px]"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <motion.button
          variants={buttonVariants}
          className="cursor-pointer bg-[#171717] text-white text-lg font-bold py-4 rounded-[6px] shadow-md transition-transform active:scale-95"
          type="submit"
        >
          {!isSubmitting ? 'Login' : 'Verifying...'}
        </motion.button>
      </motion.div>
      </form>
    </main>
  );
}
