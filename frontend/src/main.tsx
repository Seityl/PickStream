import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider, createRoutesFromElements, Route } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import './index.css';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider } from './context/AuthContext';
import { RedirectIfLoggedIn } from './components/RedirectIfLoggedIn';
import ProtectedLayout from './layouts/ProtectedLayout';
import Home, { homeLoader }  from './pages/Home';
import Login from './pages/Login';
import MaterialRequestList, { materialRequestLoader } from './pages/MaterialRequestList';
import PageLoader from './components/PageLoader';
import CrateReceiving, { crateReceivingLoader } from './pages/CrateReceiving';
import VerificationList, { verificationLoader } from './pages/Verification';
import CrateVerification from './pages/CrateVerification';
import ItemVerification from './pages/ItemVerification';
import CrateTransit, { crateTransitLoader } from './pages/CrateTransit';
import TransitList, { transitLoader } from './pages/Transit';
import ReceivingList, { receivingLoader } from './pages/Receiving';
import ItemGroupsView, { itemGroupsLoader } from './pages/ItemGroupsView';
import Printers, { printersViewLoader } from './pages/Printers';
import Picking, { pickingViewLoader } from './pages/Picking';
import Profile, { profileLoader } from './pages/Profile';
import IdentifierLookup, { IdentifierLookupLoader } from './pages/IdentifierLookup';
import ItemIdentifierDetail from './pages/ItemIdentifierDetail';
import TabLayout from './layouts/TabLayout';
import Tools from './pages/Tools';
import Crate, { crateLoader } from './pages/Crate';
import CrateCheck from './pages/CrateCheck';
import Notifications, { notificationsLoader } from './pages/Notifications';
import ErrorPage from './pages/Error';

const queryClient = new QueryClient();

const router = createBrowserRouter(createRoutesFromElements(
  <Route path="pick_stream">
    <Route path="login" element={
      <RedirectIfLoggedIn>
        <Login />
      </RedirectIfLoggedIn>
    } />
    <Route element={<ProtectedLayout />} errorElement={<ErrorPage />}>
      <Route element={<TabLayout/>}>
        <Route path="" element={<Home />} loader={homeLoader}/>
        <Route path="tools" element={<Tools/>}/>
        <Route path="profile" element={<Profile />} loader={profileLoader} />
        <Route path="notifications" element={<Notifications />} loader={notificationsLoader} />
        <Route path="tools/identifier-lookup" element={<IdentifierLookup/>} loader={IdentifierLookupLoader} />
        <Route path="tools/item-lookup/:id" element={<ItemIdentifierDetail />}/>
        <Route path="tools/active-crate" element={<Crate />} loader={crateLoader} />
        <Route path="tools/crate-check" element={<CrateCheck />} />
        <Route path="transit" element={<TransitList />} loader={transitLoader}/>
        <Route path="transit/:crateId" element={<CrateTransit />} loader={crateTransitLoader} errorElement={<ErrorPage />}/>
        <Route path="receiving" element={<ReceivingList />} loader={receivingLoader}/>
        <Route path="receiving/:crateId" element={<CrateReceiving />} loader={crateReceivingLoader} errorElement={<ErrorPage />}/>
        <Route path="verification" element={<VerificationList />} loader={verificationLoader}/>
        <Route path="verification/crate/:crate_code" element={<CrateVerification />} errorElement={<ErrorPage />}/>
        <Route path="verification/item/:identifier_code" element={<ItemVerification />} errorElement={<ErrorPage />}/>
        <Route path="material-requests" errorElement={<ErrorPage />}>
          <Route
            index
            element={<MaterialRequestList />}
            loader={materialRequestLoader}
            hydrateFallbackElement={<PageLoader variant="entertaining" />}
          />
          <Route path=":material_request" element={<ItemGroupsView />} loader={itemGroupsLoader} hydrateFallbackElement={<div />} />
        </Route>
        <Route path="printers" element={<Printers />} loader={printersViewLoader} errorElement={<ErrorPage />}/>
        <Route path="picking" element={<Picking />} loader={pickingViewLoader} errorElement={<ErrorPage />} hydrateFallbackElement={<div />} />
      </Route>
    </Route>
  </Route>
));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
        <ToastContainer />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
);
