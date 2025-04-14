import {useLoaderData} from 'react-router';
import { getNotifications } from '../../utils/api';

function Notifications() {
  const notifications = useLoaderData();
  return (
    <div>Notifications</div>
  )
}

export default Notifications;


export async function notificationsLoader() {
  const user = localStorage.getItem('user');
  return await getNotifications(user!);
}
