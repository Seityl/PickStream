export async function getCurrentUser() {
  const user = localStorage.getItem('user');
  if (user) return user;

  const res = await fetch('/api/method/frappe.auth.get_logged_user', {
    credentials: 'include',
  });

  if (!res.ok) {
    throw new Error('Failed to fetch user');
  }

  const data = await res.json();
  localStorage.setItem('user', data.message);
  return data.message;
}
