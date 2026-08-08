import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { LoginPage } from './components/LoginPage.jsx'
import { SignUpPage } from './components/SignUpPage.jsx'
import { ConnectedHomePage } from './components/ConnectedHomePage.jsx'
import { SplashScreen } from './components/SplashScreen.jsx'
import { useState, useCallback } from 'react'

function ProtectedRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  const [backendReady, setBackendReady] = useState(false)
  const handleReady = useCallback(() => setBackendReady(true), [])

  if (!backendReady) {
    return <SplashScreen onReady={handleReady} />
  }

  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/home" element={<ProtectedRoute><ConnectedHomePage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}