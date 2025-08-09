// Original validateSession function - commented for rollback
// export async function validateSession(): Promise<boolean> {
//   try {
//     const res = await fetch('/api/method/frappe.auth.get_logged_user', {
//       credentials: 'include',
//     });
//     if (!res.ok) {
//       return false;
//     }
//     const data = await res.json();
//     return data.message && data.message !== 'Guest';
//   } catch (error) {
//     return false;
//   }
// }

// Enhanced session validation with better error handling
export async function validateSession(): Promise<boolean> {
  try {
    const res = await fetch('/api/method/frappe.auth.get_logged_user', {
      credentials: 'include',
      headers: {
        'Cache-Control': 'no-cache',
      },
    });
    if (!res.ok) {
      return false;
    }
    const data = await res.json();
    return data.message && data.message !== 'Guest';
  } catch (error) {
    console.warn('Session validation failed:', error);
    return false;
  }
}

export async function getCurrentUser(): Promise<string | null> {
  try {
    const user = localStorage.getItem('user');
    if (user && user !== 'null' && user !== 'undefined') {
      return user;
    }

    const res = await fetch('/api/method/frappe.auth.get_logged_user', {
      credentials: 'include',
    });

    if (!res.ok) {
      localStorage.removeItem('user');
      return null;
    }

    const data = await res.json();
    
    if (data.message && data.message !== 'Guest') {
      const isSessionValid = await validateSession();
      if (isSessionValid) {
        localStorage.setItem('user', data.message);
        return data.message;
      }
    }
    
    localStorage.removeItem('user');
    return null;
  } catch (error) {
    localStorage.removeItem('user');
    return null;
  }
}

// Original clearUserSession function - commented for rollback
// export function clearUserSession(): void {
//   localStorage.removeItem('user');
// }

// Enhanced session management
export function clearUserSession(): void {
  localStorage.removeItem('user');
  // Clear any other auth-related storage if needed
}

// Session monitoring functionality
let sessionCheckInterval: NodeJS.Timeout | null = null;
let onSessionExpired: (() => void) | null = null;

export function startSessionMonitoring(onExpired: () => void, intervalMs: number = 300000): void {
  // Stop any existing monitoring
  stopSessionMonitoring();
  
  onSessionExpired = onExpired;
  
  sessionCheckInterval = setInterval(async () => {
    const isValid = await validateSession();
    if (!isValid && onSessionExpired) {
      console.warn('Session expired, triggering logout');
      onSessionExpired();
    }
  }, intervalMs);
}

export function stopSessionMonitoring(): void {
  if (sessionCheckInterval) {
    clearInterval(sessionCheckInterval);
    sessionCheckInterval = null;
  }
  onSessionExpired = null;
}

// Helper function to check if an error is authentication-related
export function isAuthenticationError(error: any): boolean {
  if (!error) return false;
  
  // Check for common authentication error patterns
  const status = error.status || error.response?.status;
  const message = error.message || error.response?.data?.message || '';
  
  return (
    status === 401 ||
    status === 403 ||
    message.toLowerCase().includes('not permitted') ||
    message.toLowerCase().includes('authentication') ||
    message.toLowerCase().includes('unauthorized')
  );
}
