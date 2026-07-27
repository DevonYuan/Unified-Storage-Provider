import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { LoginPage } from './components/LoginPage.jsx'
import { SignUpPage } from './components/SignUpPage.jsx'
import { HomePage } from './components/HomePage.jsx'
import { ConnectedHomePage } from './components/ConnectedHomePage.jsx'
import { useEffect } from 'react'

function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="login-page login-page__loading">
        <span className="login-page__loading-text">Loading...</span>
      </div>
    )
  }

  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="login-page login-page__loading">
        <span className="login-page__loading-text">Loading...</span>
      </div>
    )
  }

  return user ? <Navigate to="/" replace /> : children
}

function HomeRoute() {
  const { user, isLoading, isGoogleConnected, isCheckingConnection, checkGoogleConnection } = useAuth()

  useEffect(() => {
    if (user) {
      console.log('User logged in, checking Google connection...')
      checkGoogleConnection()
    }
  }, [user, checkGoogleConnection])

  console.log('HomeRoute state:', { user, isLoading, isGoogleConnected, isCheckingConnection })

  if (isLoading || isCheckingConnection) {
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
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/signup" element={<PublicRoute><SignUpPage /></PublicRoute>} />
          <Route path="/" element={<ProtectedRoute><HomeRoute /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}