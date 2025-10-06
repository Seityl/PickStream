import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { motion } from 'motion/react';
import { Eye, EyeOff, Mail, Lock, AlertCircle, LucideIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import logo from '../../public/logo.svg'

// Type definitions
interface FormErrors {
  email: string;
  password: string;
}

interface FormTouched {
  email: boolean;
  password: boolean;
}

interface EnhancedInputProps {
  type: string;
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur: () => void;
  error: string;
  touched: boolean;
  icon: LucideIcon;
  rightElement?: React.ReactNode;
  disabled?: boolean;
  onKeyPress?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

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

// Enhanced input component moved outside the main component
const EnhancedInput = ({ 
  type, 
  placeholder, 
  value, 
  onChange, 
  onBlur, 
  error, 
  touched, 
  icon: Icon, 
  rightElement,
  disabled = false,
  onKeyPress
}: EnhancedInputProps): React.JSX.Element => (
  <motion.div variants={inputVariants} className="relative">
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Icon className={`h-5 w-5 ${error && touched ? 'text-red-500' : 'text-gray-400'} transition-colors`} />
      </div>
      <input
        className={`w-full pl-10 pr-${rightElement ? '12' : '4'} py-4 rounded-lg border-2 transition-all duration-200 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
          error && touched
            ? 'border-red-300 bg-red-50 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-200 bg-white hover:border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        }`}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        onKeyPress={onKeyPress}
        disabled={disabled}
        autoComplete={type === 'email' ? 'username' : 'current-password'}
      />
      {rightElement && (
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
          {rightElement}
        </div>
      )}
    </div>
    {error && touched && (
      <motion.div 
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-1 flex items-center text-red-600 text-sm"
      >
        <AlertCircle className="h-4 w-4 mr-1" />
        {error}
      </motion.div>
    )}
  </motion.div>
);

export default function Login(): React.JSX.Element {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errors, setErrors] = useState<FormErrors>({ email: '', password: '' });
  const [touched, setTouched] = useState<FormTouched>({ email: false, password: false });
  const [shouldShake, setShouldShake] = useState<boolean>(false);
  const { user, signIn, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && user) {
      navigate('/pick_stream', { replace: true });
    }
  }, [user, isLoading, navigate]);

  // Real-time validation
  const validateEmail = (email: string): string => {
    if (!email.trim()) return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return 'Please enter a valid email address';
    return '';
  };

  const validatePassword = (password: string): string => {
    if (!password.trim()) return 'Password is required';
    if (password.length < 6) return 'Password must be at least 6 characters';
    return '';
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const value = e.target.value;
    setEmail(value);
    if (touched.email) {
      setErrors(prev => ({ ...prev, email: validateEmail(value) }));
    }
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const value = e.target.value;
    setPassword(value);
    if (touched.password) {
      setErrors(prev => ({ ...prev, password: validatePassword(value) }));
    }
  };

  const handleBlur = (field: keyof FormTouched): void => {
    setTouched(prev => ({ ...prev, [field]: true }));
    if (field === 'email') {
      setErrors(prev => ({ ...prev, email: validateEmail(email) }));
    } else {
      setErrors(prev => ({ ...prev, password: validatePassword(password) }));
    }
  };

  const isFormValid = (): boolean => {
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    return !emailError && !passwordError;
  };

  const isButtonDisabled: boolean = isSubmitting || !isFormValid();

  async function handleSubmit(e?: React.FormEvent<HTMLButtonElement> | React.KeyboardEvent<HTMLInputElement>): Promise<void> {
    e?.preventDefault();
    
    // Mark all fields as touched for validation display
    setTouched({ email: true, password: true });
    
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    
    setErrors({ email: emailError, password: passwordError });
    
    if (emailError || passwordError) {
      setShouldShake(true);
      setTimeout(() => setShouldShake(false), 400);
      return;
    }
    
    setIsSubmitting(true);
    try {
      const result = await signIn(email, password);
      if (result?.error) {
        toast.error(result.msg || 'Invalid credentials. Please try again.');
        setShouldShake(true);
        setTimeout(() => setShouldShake(false), 400);
      } else {
        toast.success('Welcome back!');
        navigate('/pick_stream', { replace: true });
      }
    } catch (err: unknown) {
      toast.error('Login failed. Please check your connection and try again.');
      setShouldShake(true);
      setTimeout(() => setShouldShake(false), 400);
    } finally {
      setIsSubmitting(false);
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <motion.div
          variants={imageVariants}
          initial="hidden"
          animate="show"
          className="text-center mb-8"
        >
          <img src={logo} alt="Pick Stream Logo" className="h-32 w-auto mx-auto" />
          <h1 className="mt-4 text-2xl font-bold text-gray-900">Pick Stream</h1>
          <p className="mt-2 text-gray-600">Sign in to continue</p>
        </motion.div>

        {/* Login Card */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate={shouldShake ? "shake" : "show"}
          className="bg-white py-8 px-6 shadow-lg rounded-xl border border-gray-200"
        >
          <div className="space-y-6">
            
            {/* Email Input */}
            <EnhancedInput
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={handleEmailChange}
              onBlur={() => handleBlur('email')}
              onKeyPress={handleKeyPress}
              error={errors.email}
              touched={touched.email}
              icon={Mail}
              disabled={isSubmitting}
            />

            {/* Password Input */}
            <EnhancedInput
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={handlePasswordChange}
              onBlur={() => handleBlur('password')}
              onKeyPress={handleKeyPress}
              error={errors.password}
              touched={touched.password}
              icon={Lock}
              disabled={isSubmitting}
              rightElement={
                <button
                  type="button"
                  className="text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isSubmitting}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              }
            />

            {/* Submit Button */}
            <motion.button
              variants={buttonVariants}
              type="button"
              onClick={handleSubmit}
              disabled={isButtonDisabled}
              className={`w-full flex justify-center items-center py-4 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                isButtonDisabled
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 active:transform active:scale-[0.98]'
              }`}
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </motion.button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}