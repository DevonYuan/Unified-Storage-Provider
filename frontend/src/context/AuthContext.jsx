import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/client.js'

const AuthContext = createContext(undefined)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleConnected, setIsGoogleConnected] = useState(false)
  const [isCheckingConnection, setIsCheckingConnection] = useState(false)

  const checkGoogleConnection = async () => {
    setIsCheckingConnection(true)
    try {
      console.log('Checking Google Drive connection...')
      const response = await authApi.listAccounts()
      console.log('Accounts response:', response)
      
      // Handle different response structures
      const accounts = Array.isArray(response) ? response : (response.accounts || [])
      console.log('Parsed accounts array:', accounts)
      
      const googleAccount = accounts.find(acc => acc.provider === 'google_drive')
      console.log('Google account found:', googleAccount)
      setIsGoogleConnected(!!googleAccount)
      console.log('isGoogleConnected set to:', !!googleAccount)
    } catch (error) {
      console.error('Failed to check Google Drive connection:', error)
      setIsGoogleConnected(false)
    } finally {
      setIsCheckingConnection(false)
    }
  }

  const login = () => {
    const newUser = {
      id: Math.random().toString(36).substring(2, 11),
      email: `user-${Date.now()}@omnidrive.local`,
    }
    setUser(newUser)
    localStorage.setItem('omnidrive_user', JSON.stringify(newUser))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('omnidrive_user')
    setIsGoogleConnected(false)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isGoogleConnected, isCheckingConnection, checkGoogleConnection, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
