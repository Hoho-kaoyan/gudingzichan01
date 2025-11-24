import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Login from './pages/Login'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import UserManagement from './pages/UserManagement'
import AssetManagement from './pages/AssetManagement'
import AssetHistory from './pages/AssetHistory'
import TransferManagement from './pages/TransferManagement'
import ReturnManagement from './pages/ReturnManagement'
import ApprovalManagement from './pages/ApprovalManagement'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="assets" element={<AssetManagement />} />
            <Route path="assets/:assetId/history" element={<AssetHistory />} />
            <Route path="transfers" element={<TransferManagement />} />
            <Route path="returns" element={<ReturnManagement />} />
            <Route path="approvals" element={<ApprovalManagement />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App
