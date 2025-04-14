import axios from 'axios';
import { FrappeApp } from 'frappe-js-sdk';

const clientConfig = {
  baseUrl: 'http://10.0.10.122/api/method',
  domain: 'http://10.0.10.122',
};

const frappeApp = new FrappeApp(clientConfig.domain);


export const frappeClient = frappeApp.call();
export const frappeAuth = frappeApp.auth();

 
