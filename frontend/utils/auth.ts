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
      localStorage.setItem('user', data.message);
      return data.message;
    }
    
    localStorage.removeItem('user');
    return null;
  } catch (error) {
    localStorage.removeItem('user');
    return null;
  }
}

export function clearUserSession(): void {
  localStorage.removeItem('user');
}
