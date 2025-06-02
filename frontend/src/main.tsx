import { StrictMode, JSX } from 'react';
import { createRoot } from 'react-dom/client';
import { Routes, Route, createBrowserRouter, RouterProvider, createRoutesFromElements, Navigate } from 'react-router';
import { FrappeProvider } from 'frappe-react-sdk';
import { AnimatePresence } from 'motion/react';
import { ToastContainer } from 'react-toastify';
import './index.css';
import { useFrappeAuth } from 'frappe-react-sdk';
import ProtectedLayout from './layouts/ProtectedLayout';
import Home from './pages/Home';
import Login from './pages/Login';
import MaterialRequestList, {materialRequestLoader} from './pages/MaterialRequestList';
import VerificationList from './pages/Verification';
import CrateVerification from './pages/CrateVerification';
import CrateReceiving from './pages/CrateReceiving';
import CrateTransit from './pages/CrateTransit';
import TransitList from './pages/Transit';
import ReceivingList from './pages/Receiving';
import ItemGroupsView, {itemGroupsLoader} from './pages/ItemGroupsView';
import ItemGroupView, {itemGroupLoader} from './pages/ItemGroupView';
import Printers, {printersViewLoader} from './pages/Printers';
import Picking, {pickingViewLoader} from './pages/Picking';
import Profile, {profileLoader} from './pages/Profile';
import IdentifierLookup from './pages/IdentifierLookup';
import ItemIdentifierDetail from './pages/ItemIdentifierDetail';
import TabLayout from './layouts/TabLayout';
import Tools from './pages/Tools';
import Crate, {CrateLoader} from './pages/Crate';
import Notifications, {notificationsLoader} from './pages/Notifications';
import ErrorPage from './pages/Error';

interface RedirectIfLoggedInProps {
  children: JSX.Element;
}

const RedirectIfLoggedIn = ({ children }: RedirectIfLoggedInProps) => {
  const { currentUser } = useFrappeAuth();
  return currentUser ? <Navigate to="/pick_stream" replace /> : children;
}

const router = createBrowserRouter(createRoutesFromElements(
  <Route path="pick_stream">
    
      <Route path="login" element={
        <RedirectIfLoggedIn>
        <Login />
        </RedirectIfLoggedIn>
      } />
    
    <Route element={<ProtectedLayout />} errorElement={<ErrorPage />}>
      <Route element={<TabLayout/>}>
        <Route path="" element={<Home />} />
        <Route path="tools" element={<Tools/>}/>
        <Route path="profile" element={<Profile />} loader={profileLoader} />
        <Route path="notifications" element={<Notifications />} loader={notificationsLoader} />
        <Route path="tools/identifier-lookup" element={<IdentifierLookup/>} />
        <Route path="tools/item-lookup/:id" element={<ItemIdentifierDetail />}/>
        <Route path="tools/crate" element={<Crate />}/>
        <Route path="transit" element={<TransitList />}/>
        <Route path="transit/:crateId" element={<CrateTransit />} errorElement={<ErrorPage />}/>
        <Route path="receiving" element={<ReceivingList />}/>
        <Route path="receiving/:crateId" element={<CrateReceiving />} errorElement={<ErrorPage />}/>
        <Route path="verification" element={<VerificationList />}/>
        <Route path="verification/:crateId" element={<CrateVerification />} errorElement={<ErrorPage />}/>
        <Route path="material-requests" errorElement={<ErrorPage />}>
        <Route index element={<MaterialRequestList />} loader={materialRequestLoader} />
        {/* <Route path=":material_request/:item_group" element={<ItemGroupView />} loader={itemGroupLoader}/> */}
        <Route path=":material_request" element={<ItemGroupsView />} loader={itemGroupsLoader}/>
      </Route>

      <Route path="printers" element={<Printers />} loader={printersViewLoader} errorElement={<ErrorPage />}/>
      </Route>
   
      <Route path="picking" element={<Picking />} loader={pickingViewLoader} errorElement={<ErrorPage />}/>

      
    </Route>
  </Route>
  ));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <FrappeProvider url="http://10.0.10.122">
      <RouterProvider router={router} />
      <ToastContainer/>
    </FrappeProvider>
  </StrictMode>
);
