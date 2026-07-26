import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(undefined)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

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
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
