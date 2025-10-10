import { useState, useEffect } from 'react';
import { FaBox, FaWarehouse, FaClipboardList, FaTruck, FaBoxOpen, FaBoxes, FaCubes, FaDolly } from 'react-icons/fa';

type LoaderVariant = 'default' | 'minimal' | 'entertaining';

interface PageLoaderProps {
  variant?: LoaderVariant;
  message?: string;
  className?: string;
}

const loadingMessages = [
  "Gathering your items...",
  "Checking warehouse inventory...",
  "Preparing pick lists...",
  "Organizing material requests...",
  "Scanning item groups...",
  "Loading crate information...",
  "Fetching warehouse data...",
  "Optimizing pick routes...",
  "Calculating inventory levels...",
  "Syncing with warehouse system...",
  "Processing batch data...",
  "Almost there...",
];

const funMessages = [
  "Teaching robots to count boxes...",
  "Convincing the database to cooperate...",
  "Negotiating with the backend...",
  "Asking the warehouse nicely...",
  "Untangling some data spaghetti...",
  "Bribing the cache with cookies...",
  "Waking up sleepy servers...",
  "Loading with extra enthusiasm...",
];

const icons = [FaBox, FaWarehouse, FaClipboardList, FaTruck, FaBoxOpen, FaBoxes, FaCubes, FaDolly];

/**
 * Enhanced PageLoader component for long-running operations
 * Features rotating messages, progress indicators, and animated icons
 */
export default function PageLoader({
  variant = 'default',
  message,
  className = ''
}: PageLoaderProps) {
  const [currentMessage, setCurrentMessage] = useState(message || loadingMessages[0]);
  const [messageIndex, setMessageIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [iconIndex, setIconIndex] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showFunMessages, setShowFunMessages] = useState(false);

  // Track elapsed time
  useEffect(() => {
    const timeInterval = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timeInterval);
  }, []);

  // Prevent body scroll when loader is active (for non-minimal variants)
  useEffect(() => {
    if (variant !== 'minimal') {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = 'unset';
      };
    }
  }, [variant]);

  // Switch to fun messages after 8 seconds
  useEffect(() => {
    if (elapsedTime >= 8 && variant === 'entertaining') {
      setShowFunMessages(true);
    }
  }, [elapsedTime, variant]);

  // Rotate through loading messages every 2.5 seconds
  useEffect(() => {
    if (message) return; // Don't rotate if custom message provided

    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => {
        const messages = showFunMessages ? funMessages : loadingMessages;
        const next = (prev + 1) % messages.length;
        setCurrentMessage(messages[next]);
        return next;
      });
    }, 2500);

    return () => clearInterval(messageInterval);
  }, [message, showFunMessages]);

  // Rotate icons every 2 seconds
  useEffect(() => {
    const iconInterval = setInterval(() => {
      setIconIndex((prev) => (prev + 1) % icons.length);
    }, 2000);

    return () => clearInterval(iconInterval);
  }, []);

  // Simulate progress (but never reach 100% until actual completion)
  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return 95; // Cap at 95% to indicate still loading
        const increment = Math.random() * 3 + 1;
        return Math.min(prev + increment, 95);
      });
    }, 500);

    return () => clearInterval(progressInterval);
  }, []);

  if (variant === 'minimal') {
    return (
      <div className={`flex items-center justify-center min-h-[200px] overflow-hidden ${className}`}>
        <div className="flex flex-col items-center space-y-3">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
          {message && (
            <p className="text-sm text-gray-600 font-medium">{message}</p>
          )}
        </div>
      </div>
    );
  }

  if (variant === 'entertaining') {
    const CurrentIcon = icons[iconIndex];

    return (
      <div className={`fixed inset-0 flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 animate-gradientShift overflow-hidden z-50 ${className}`}>
        <div className="text-center p-8 max-w-md mx-4">
          {/* Animated Icon Container */}
          <div className="relative mb-8 h-40 flex items-center justify-center">
            {/* Multiple pulsing background circles */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-40 h-40 bg-blue-100 rounded-full animate-ping opacity-10"></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-32 h-32 bg-purple-100 rounded-full animate-ping opacity-20" style={{ animationDelay: '0.5s' }}></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 bg-blue-200 rounded-full animate-pulse"></div>
            </div>

            {/* Orbiting mini icons */}
            {elapsedTime > 5 && (
              <>
                <div className="absolute inset-0 flex items-center justify-center animate-spin" style={{ animationDuration: '8s' }}>
                  <FaBox className="text-blue-400 text-lg absolute top-0" />
                </div>
                <div className="absolute inset-0 flex items-center justify-center animate-spin" style={{ animationDuration: '6s', animationDirection: 'reverse' }}>
                  <FaCubes className="text-purple-400 text-lg absolute bottom-0" />
                </div>
              </>
            )}

            {/* Main icon with rotation */}
            <div className="relative flex items-center justify-center">
              <div className="bg-white p-6 rounded-2xl shadow-2xl border-4 border-blue-100 transform transition-all duration-500 hover:scale-110 animate-iconBounce">
                <CurrentIcon
                  className="text-blue-600 text-6xl transition-all duration-500"
                  style={{
                    animation: elapsedTime > 10 ? 'spin 2s linear infinite, bounce 1s ease-in-out infinite' : 'bounce 1s ease-in-out infinite'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Loading message with fade transition */}
          <div className="mb-6 min-h-[80px]">
            <h2
              key={currentMessage}
              className={`text-2xl font-bold mb-2 animate-fadeIn ${showFunMessages ? 'text-purple-700' : 'text-gray-800'}`}
            >
              {currentMessage}
            </h2>
            <p className="text-gray-600">
              {elapsedTime < 5
                ? 'This might take a moment...'
                : elapsedTime < 10
                  ? 'Still working on it...'
                  : 'Thanks for your patience!'}
            </p>
            {elapsedTime > 8 && (
              <p className="text-sm text-purple-500 mt-2 animate-fadeIn">
                ⏱️ {elapsedTime}s elapsed
              </p>
            )}
          </div>

          {/* Enhanced Progress bar with glow effect */}
          <div className="mb-4">
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner">
              <div
                className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 bg-[length:200%_100%] animate-shimmer transition-all duration-300 ease-out rounded-full relative"
                style={{
                  width: `${progress}%`,
                  boxShadow: elapsedTime > 5 ? '0 0 20px rgba(147, 51, 234, 0.5)' : 'none'
                }}
              >
                <div className="absolute inset-0 bg-white opacity-30 animate-pulse"></div>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 font-medium">{Math.round(progress)}% complete</p>
          </div>

          {/* Animated elements based on elapsed time */}
          <div className="flex justify-center space-x-3 mt-6">
            {elapsedTime < 8 ? (
              // Floating boxes animation
              [0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="w-3 h-3 bg-gradient-to-br from-blue-500 to-purple-500 rounded-sm"
                  style={{
                    animation: `float 1.5s ease-in-out ${i * 0.15}s infinite`
                  }}
                ></div>
              ))
            ) : (
              // Wave animation for longer loads
              [0, 1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="w-2 rounded-full bg-gradient-to-t from-blue-500 to-purple-500"
                  style={{
                    height: '20px',
                    animation: `wave 1.2s ease-in-out ${i * 0.1}s infinite`
                  }}
                ></div>
              ))
            )}
          </div>

          {/* Encouraging message after long wait */}
          {elapsedTime > 12 && (
            <div className="mt-6 p-3 bg-purple-50 border border-purple-200 rounded-lg animate-fadeIn">
              <p className="text-sm text-purple-700 font-medium">
                Complex operations in progress
              </p>
            </div>
          )}
        </div>

        {/* Floating particles in background - with fixed positions for hydration */}
        {elapsedTime > 6 && (
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            {[
              { left: 10, top: 20, duration: 7, delay: 0.5 },
              { left: 80, top: 30, duration: 6, delay: 1 },
              { left: 25, top: 60, duration: 8, delay: 0.2 },
              { left: 65, top: 15, duration: 9, delay: 1.5 },
              { left: 45, top: 75, duration: 7.5, delay: 0.8 },
              { left: 90, top: 50, duration: 6.5, delay: 0.3 },
              { left: 15, top: 85, duration: 8.5, delay: 1.2 },
              { left: 55, top: 40, duration: 7.8, delay: 0.6 },
            ].map((particle, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 bg-blue-300 rounded-full opacity-40"
                style={{
                  left: `${particle.left}%`,
                  top: `${particle.top}%`,
                  animation: `floatAround ${particle.duration}s ease-in-out ${particle.delay}s infinite`
                }}
              ></div>
            ))}
          </div>
        )}

        {/* Enhanced inline animations */}
        <style dangerouslySetInnerHTML={{
          __html: `
            @keyframes fadeIn {
              from { opacity: 0; transform: translateY(-10px); }
              to { opacity: 1; transform: translateY(0); }
            }

            @keyframes shimmer {
              0% { background-position: 200% 0; }
              100% { background-position: -200% 0; }
            }

            @keyframes float {
              0%, 100% { transform: translateY(0) rotate(0deg); }
              50% { transform: translateY(-12px) rotate(180deg); }
            }

            @keyframes wave {
              0%, 100% { height: 10px; }
              50% { height: 25px; }
            }

            @keyframes iconBounce {
              0%, 100% { transform: translateY(0); }
              50% { transform: translateY(-10px); }
            }

            @keyframes floatAround {
              0%, 100% { transform: translate(0, 0); }
              25% { transform: translate(30px, -30px); }
              50% { transform: translate(-20px, -60px); }
              75% { transform: translate(-40px, -30px); }
            }

            @keyframes gradientShift {
              0%, 100% {
                background: linear-gradient(135deg, rgb(239 246 255) 0%, rgb(255 255 255) 50%, rgb(250 245 255) 100%);
              }
              50% {
                background: linear-gradient(135deg, rgb(250 245 255) 0%, rgb(255 255 255) 50%, rgb(239 246 255) 100%);
              }
            }

            .animate-fadeIn {
              animation: fadeIn 0.5s ease-out;
            }

            .animate-shimmer {
              animation: shimmer 2s linear infinite;
            }

            .animate-iconBounce {
              animation: iconBounce 2s ease-in-out infinite;
            }

            .animate-gradientShift {
              animation: gradientShift 10s ease-in-out infinite;
            }
          `
        }} />
      </div>
    );
  }

  // Default variant
  const CurrentIcon = icons[iconIndex];

  return (
    <div className={`fixed inset-0 flex items-center justify-center bg-gray-50 overflow-hidden z-50 ${className}`}>
      <div className="text-center p-8 bg-white rounded-2xl shadow-xl border border-gray-200 max-w-md mx-4 relative overflow-hidden">
        {/* Animated background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-transparent to-purple-50/50 animate-pulse"></div>

        {/* Content */}
        <div className="relative">
          {/* Animated Icon */}
          <div className="relative mb-6 h-28 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 bg-blue-100 rounded-full animate-ping opacity-20"></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-20 h-20 bg-blue-100 rounded-full animate-pulse"></div>
            </div>
            <div className="relative flex items-center justify-center">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-5 rounded-xl border-2 border-blue-200 shadow-lg transform transition-transform duration-500 hover:scale-110">
                <CurrentIcon className="text-blue-600 text-5xl animate-bounce" />
              </div>
            </div>
          </div>

          {/* Loading message */}
          <div className="mb-6 min-h-[60px]">
            <h3
              key={currentMessage}
              className="text-xl font-semibold text-gray-900 mb-2 animate-fadeIn"
            >
              {currentMessage}
            </h3>
            <p className="text-sm text-gray-600">
              {elapsedTime < 5 ? 'Processing your request...' : 'This is taking a bit longer than usual...'}
            </p>
            {elapsedTime > 8 && (
              <p className="text-xs text-gray-500 mt-1">
                {elapsedTime}s elapsed
              </p>
            )}
          </div>

          {/* Enhanced Progress bar */}
          <div className="mb-4">
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
              <div
                className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-purple-500 transition-all duration-500 ease-out rounded-full relative"
                style={{ width: `${progress}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmerBar"></div>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 font-medium">
              {Math.round(progress)}% complete
            </p>
          </div>

          {/* Enhanced dots animation */}
          <div className="flex justify-center space-x-2.5">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="w-2.5 h-2.5 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full shadow-sm"
                style={{
                  animation: `dotPulse 1.5s ease-in-out ${i * 0.2}s infinite`
                }}
              ></div>
            ))}
          </div>
        </div>
      </div>

      {/* Enhanced inline animations */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-5px); }
            to { opacity: 1; transform: translateY(0); }
          }

          @keyframes shimmerBar {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
          }

          @keyframes dotPulse {
            0%, 100% {
              transform: scale(1);
              opacity: 1;
            }
            50% {
              transform: scale(1.3);
              opacity: 0.7;
            }
          }

          .animate-fadeIn {
            animation: fadeIn 0.4s ease-out;
          }

          .animate-shimmerBar {
            animation: shimmerBar 2s ease-in-out infinite;
          }
        `
      }} />
    </div>
  );
}
