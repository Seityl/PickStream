import { FrappeApp } from 'frappe-js-sdk';

const clientConfig = {
  baseUrl: import.meta.env.VITE_FRAPPE_URL || 'http://10.0.10.92',
  domain: import.meta.env.VITE_FRAPPE_URL || 'http://10.0.10.92',
};

const frappeApp = new FrappeApp("");

export const frappeClient = frappeApp.call();
export const frappeAuth = frappeApp.auth();