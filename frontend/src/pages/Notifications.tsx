import {useLoaderData} from 'react-router';
import { getNotifications } from '../../utils/api';
import { getCurrentUser } from '../../utils/auth';

function Notifications() {
  const notifications = useLoaderData();
  return (
    <div>Notifications</div>
  )
}

export default Notifications;


export async function notificationsLoader() {
  const user = await getCurrentUser();
  return await getNotifications(user!);
}
