import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { LoginPage } from './components/LoginPage.jsx'
import { SignUpPage } from './components/SignUpPage.jsx'
import { HomePage } from './components/HomePage.jsx'
import { ConnectedHomePage } from './components/ConnectedHomePage.jsx'
import { useEffect } from 'react'

function ProtectedRoute({ children }) {
  const { user } = useAuth()
  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user } = useAuth()
  return user ? <Navigate to="/home" replace /> : children
}

function HomeRoute() {
  const { user, isGoogleConnected, isCheckingConnection, checkGoogleConnection } = useAuth()

  useEffect(() => {
    if (user) {
      console.log('User logged in, checking Google connection...')
      checkGoogleConnection()
    }
  }, [user, checkGoogleConnection])

  console.log('HomeRoute state:', { user, isGoogleConnected, isCheckingConnection })

  if (isCheckingConnection) {
    return (
      <div className="login-page login-page__loading">
        <span className="login-page__loading-text">Loading...</span>
      </div>
    )
  }

  console.log('Rendering component based on isGoogleConnected:', isGoogleConnected)
  return isGoogleConnected ? <ConnectedHomePage /> : <HomePage />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/home" element={<ProtectedRoute><HomeRoute /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}