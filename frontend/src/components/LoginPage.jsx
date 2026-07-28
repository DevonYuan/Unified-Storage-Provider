import { useAuth } from '../context/AuthContext.jsx'
import { HardDrive } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'
import '../styles/LoginPage.css'

function ProviderBadges() {
  return (
    <div className="login-page__providers">
      <span className="login-page__providers-label">Works with</span>
      <span className="login-page__provider">
        <span className="login-page__provider-dot login-page__provider-dot--green" />
        Google Drive
      </span>
      <span className="login-page__provider">
        <span className="login-page__provider-dot login-page__provider-dot--blue" />
        OneDrive
      </span>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleLogin = () => {
    login()
    navigate('/home')
  }

  return (
    <div className="login-page login-page__unauthenticated">
      <nav className="login-page__nav">
        <div className="login-page__brand">
          <div className="login-page__logo">
            <HardDrive className="login-page__logo-icon" size={13} />
          </div>
          <span className="login-page__brand-name">OmniDrive</span>
        </div>
      </nav>

      <main className="login-page__content">
        <div className="login-page__tagline">
          <span className="login-page__badge">
            <span className="login-page__badge-dot" />
            One storage layer. All your clouds underneath.
          </span>
        </div>

        <h1 className="login-page__headline">
          <span className="login-page__headline-line">Your files.</span>
          <span className="login-page__headline-line login-page__headline-line--muted">Not your folders.</span>
        </h1>

        <p className="login-page__subheadline">
          OmniDrive unifies Google Drive and OneDrive into a single, quiet
          workspace. No more switching tabs or guessing where a file lives.
        </p>

        <div className="login-page__buttons">
          <button
            onClick={handleLogin}
            className="login-page__btn-primary"
          >
            Open OmniDrive
            <svg className="login-page__btn-arrow" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <path d="M2 6.5H11M11 6.5L7.5 3M11 6.5L7.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <Link to="/signup" className="login-page__btn-secondary">
            Get set up
          </Link>
        </div>

        <ProviderBadges />
      </main>

      <footer className="login-page__footer">
        <span>&copy; 2026 OmniDrive</span>
        <span className="login-page__version">v0.1 &middot; design preview</span>
      </footer>
    </div>
  )
}