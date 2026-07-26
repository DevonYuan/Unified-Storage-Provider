import { useAuth } from '../context/AuthContext.jsx'
import { HardDrive, LogOut } from 'lucide-react'
import '../styles/HomePage.css'

export function HomePage() {
  const { user, logout } = useAuth()

  return (
    <div className="home-page">
      <header className="home-page__header">
        <div className="home-page__brand">
          <div className="home-page__logo">
            <HardDrive className="home-page__logo-icon" size={13} />
          </div>
          <span className="home-page__brand-name">OmniDrive</span>
        </div>
        <button
          onClick={logout}
          className="home-page__signout"
        >
          <LogOut className="home-page__signout-icon" size={14} />
          Sign out
        </button>
      </header>
      <main className="home-page__main">
        <div className="home-page__welcome">
          <p className="home-page__signed-in-label">Signed in</p>
          <h2 className="home-page__welcome-title">Welcome back.</h2>
          <p className="home-page__welcome-text">
            Your unified cloud storage workspace is on its way. Connect your providers to get started.
          </p>
          <p className="home-page__user-id">{user.id}</p>
        </div>
      </main>
    </div>
  )
}