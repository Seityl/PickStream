import axios from 'axios';
import { FrappeApp } from 'frappe-js-sdk';

const clientConfig = {
  baseUrl: 'http://10.0.10.122:8000/api/method',
  domain: 'http://10.0.10.122:8000',
};

const frappeClient = new FrappeApp(clientConfig.domain);

export default frappeClient;
