import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Routes, Route, createBrowserRouter, RouterProvider, createRoutesFromElements } from 'react-router';
import { AnimatePresence } from 'motion/react';
import './index.css';
import { AuthProvider } from './context/AuthContext';
import ProtectedLayout from './layouts/ProtectedLayout';
import Home from './pages/Home';
import Login from './pages/Login';
import MaterialRequestList, {materialRequestLoader} from './pages/MaterialRequestList';
import ItemGroupsView, {itemGroupsLoader} from './pages/ItemGroupsView';
import ItemGroupView, {itemGroupLoader} from './pages/ItemGroupView';
import Printers, {printersViewLoader} from './pages/Printers';
import Picking, {pickingViewLoader} from './pages/Picking';
import Profile, {profileLoader} from './pages/Profile';
import TabLayout from './layouts/TabLayout';
import Logs from './pages/Logs';
import Notifications, {notificationsLoader} from './pages/Notifications';
import ErrorPage from './pages/Error';

const router = createBrowserRouter(createRoutesFromElements(
  <Route path="pick_stream">
    <Route path="login" element={<Login />} />

    <Route element={<ProtectedLayout />} errorElement={<ErrorPage />}>
      <Route element={<TabLayout/>}>
        <Route path="" element={<Home />} />
        <Route path="logs" element={<Logs/>} />
        <Route path="profile" element={<Profile />} loader={profileLoader} />
        <Route path="notifications" element={<Notifications />} loader={notificationsLoader} />
      </Route>
      <Route path="material-requests" errorElement={<ErrorPage />}>
        <Route index element={<MaterialRequestList />} loader={materialRequestLoader} />
        <Route path=":material_request/:item_group" element={<ItemGroupView />} loader={itemGroupLoader}/>
        <Route path=":material_request" element={<ItemGroupsView />} loader={itemGroupsLoader}/>
      </Route>

      <Route path="picking" element={<Picking />} loader={pickingViewLoader}/>

      <Route path="printers" element={<Printers />} loader={printersViewLoader}/>
    </Route>
  </Route>
  ));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>
);
