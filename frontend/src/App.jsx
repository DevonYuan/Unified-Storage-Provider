import { AuthProvider } from './context/AuthContext.jsx'
import { LoginPage } from './components/LoginPage.jsx'

export default function App() {
  return (
    <AuthProvider>
      <LoginPage />
    </AuthProvider>
  )
}
