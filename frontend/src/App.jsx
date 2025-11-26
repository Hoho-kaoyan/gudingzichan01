import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { TransferProvider } from './contexts/TransferContext'
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
import SafetyCheckTypeManagement from './pages/SafetyCheckTypeManagement'
import SafetyCheckTaskManagement from './pages/SafetyCheckTaskManagement'
import MySafetyCheckTasks from './pages/MySafetyCheckTasks'

function App() {
  return (
    <AuthProvider>
      <TransferProvider>
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
            <Route path="safety-check-types" element={<SafetyCheckTypeManagement />} />
            <Route path="safety-check-tasks" element={<SafetyCheckTaskManagement />} />
            <Route path="my-safety-check-tasks" element={<MySafetyCheckTasks />} />
          </Route>
        </Routes>
      </Router>
      </TransferProvider>
    </AuthProvider>
  )
}

export default App
