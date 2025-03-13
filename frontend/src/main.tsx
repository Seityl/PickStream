import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import './index.css';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import Login from './pages/Login';
import MaterialRequestList from './pages/MaterialRequestList';
import MaterialRequestDetail from './pages/MaterialRequestDetail';
import CreateCrate from './pages/CreateCrate';
import Picking from './pages/Picking';
import Profile from './pages/Profile';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="pick_stream">
            <Route path="login" element={<Login />} />

            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="" element={<Home />} />

              <Route path="material-requests">
                <Route index element={<MaterialRequestList />} />
                <Route
                  path=":material_request"
                  element={<MaterialRequestDetail />}
                />
              </Route>

              <Route path="crate-crate" element={<CreateCrate />} />

              <Route path="picking">
                <Route path=":stream" element={<Picking />} />
              </Route>

              <Route path="profile" element={<Profile />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>
);
