import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  HardDrive,
  Cloud,
  Check,
  ArrowRight,
  AlertCircle,
  Loader2
} from 'lucide-react'
import '../styles/SignUpPage.css'
import { authApi } from '../api/client.js'

function ProviderBadges() {
  return (
    <div className="signup-page__providers">
      <span className="signup-page__providers-label">Works with</span>
      <span className="signup-page__provider">
        <span className="signup-page__provider-dot signup-page__provider-dot--green" />
        Google Drive
      </span>
      <span className="signup-page__provider">
        <span className="signup-page__provider-dot signup-page__provider-dot--blue" />
        OneDrive
      </span>
    </div>
  )
}

// Auth callback page - handles OAuth redirect from Google
function AuthCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('loading') // 'loading' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    async function handleCallback() {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')

      if (error) {
        setStatus('error')
        setErrorMessage(`OAuth error: ${error}`)
        return
      }

      if (!code || !state) {
        setStatus('error')
        setErrorMessage('Missing code or state parameter')
        return
      }

      const redirectUri = `${window.location.origin}/auth/callback`

      try {
        await authApi.handleOAuthCallback('google_drive', code, state, redirectUri)
        setStatus('success')
        // Redirect back to signup page after brief delay
        setTimeout(() => navigate('/signup', { replace: true }), 1500)
      } catch (err) {
        setStatus('error')
        setErrorMessage(err.message || 'Failed to connect Google Drive')
      }
    }

    handleCallback()
  }, [searchParams, navigate])

  if (status === 'loading') {
    return (
      <div className="signup-page signup-page__unauthenticated">
        <main className="signup-page__content">
          <div className="signup-page__callback-loading">
            <Loader2 className="signup-page__callback-spinner" size={40} />
            <p>Completing Google Drive connection...</p>
          </div>
        </main>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="signup-page signup-page__unauthenticated">
        <main className="signup-page__content">
          <div className="signup-page__callback-success">
            <Check className="signup-page__callback-icon" size={48} />
            <h2>Google Drive Connected!</h2>
            <p>Redirecting you back...</p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="signup-page signup-page__unauthenticated">
      <main className="signup-page__content">
        <div className="signup-page__callback-error">
          <AlertCircle className="signup-page__callback-icon" size={48} />
          <h2>Connection Failed</h2>
          <p>{errorMessage}</p>
          <button
            onClick={() => navigate('/signup', { replace: true })}
            className="signup-page__retry-btn"
          >
            Try Again
          </button>
        </div>
      </main>
    </div>
  )
}

export function SignUpPage() {
  const navigate = useNavigate()
  const [googleConnected, setGoogleConnected] = useState(false)
  const [microsoftConnected, setMicrosoftConnected] = useState(false)
  const [connecting, setConnecting] = useState(null)
  const [accounts, setAccounts] = useState([])

  // Load connected accounts on mount
  useEffect(() => {
    async function loadAccounts() {
      try {
        const data = await authApi.listAccounts()
        setAccounts(data.accounts || [])
        // Check if Google Drive is already connected
        const googleAccount = data.accounts?.find(a => a.provider === 'google_drive')
        if (googleAccount) {
          setGoogleConnected(true)
        }
      } catch (err) {
        console.error('Failed to load accounts:', err)
      }
    }
    loadAccounts()
  }, [])

  const handleGoogleDriveConnect = async () => {
    if (googleConnected) return

    setConnecting('google')

    try {
      const redirectUri = `${window.location.origin}/auth/callback`
      const { auth_url, state } = await authApi.startGoogleOAuth(redirectUri)

      // Store state in sessionStorage for validation on callback
      sessionStorage.setItem('oauth_state', state)

      // Redirect to Google OAuth
      window.location.href = auth_url
    } catch (err) {
      console.error('Failed to start Google OAuth:', err)
      setConnecting(null)
      alert(`Failed to start Google Drive connection: ${err.message}`)
    }
  }

  const handleOneDriveConnect = async () => {
    if (microsoftConnected) return
    setConnecting('microsoft')
    // Simulate connection process
    await new Promise(resolve => setTimeout(resolve, 1500))
    setMicrosoftConnected(true)
    setConnecting(null)
  }

  const handleContinue = () => {
    if (googleConnected || microsoftConnected) {
      navigate('/')
    }
  }

  const canContinue = googleConnected || microsoftConnected

  return (
    <div className="signup-page signup-page__unauthenticated">
      <nav className="signup-page__nav">
        <div className="signup-page__brand">
          <div className="signup-page__logo">
            <HardDrive className="signup-page__logo-icon" size={13} />
          </div>
          <span className="signup-page__brand-name">OmniDrive</span>
        </div>
        <a href="/login" className="signup-page__signin-link">
          Sign in
        </a>
      </nav>

      <main className="signup-page__content">
        <div className="signup-page__tagline">
          <span className="signup-page__badge">
            <span className="signup-page__badge-dot" />
            Create your unified workspace
          </span>
        </div>

        <h1 className="signup-page__headline">
          <span className="signup-page__headline-line">Connect your clouds.</span>
          <span className="signup-page__headline-line signup-page__headline-line--muted">One workspace.</span>
        </h1>

        <p className="signup-page__subheadline">
          Connect Google Drive and OneDrive in seconds. One search. One workspace. Zero folder chaos.
        </p>

        <div className="signup-page__connect-section">
          <div className="signup-page__connect-card">
            <div className="signup-page__connect-icon signup-page__connect-icon--google">
              <Cloud size={28} />
            </div>
            <div className="signup-page__connect-info">
              <h3 className="signup-page__connect-title">Google Drive</h3>
              <p className="signup-page__connect-description">
                Connect your Google account to access files from Google Drive
              </p>
            </div>
            <button
              type="button"
              className={`signup-page__connect-btn ${googleConnected ? 'signup-page__connect-btn--connected' : ''}`}
              onClick={handleGoogleDriveConnect}
              disabled={googleConnected || connecting === 'microsoft'}
            >
              {connecting === 'google' ? (
                <>
                  <Loader2 className="signup-page__btn-spinner" size={16} />
                  Connecting…
                </>
              ) : googleConnected ? (
                <>
                  <Check size={16} />
                  Connected
                </>
              ) : (
                <>
                  Connect
                  <ArrowRight size={13} />
                </>
              )}
            </button>
          </div>

          <div className="signup-page__connect-card">
            <div className="signup-page__connect-icon signup-page__connect-icon--microsoft">
              <HardDrive size={28} />
            </div>
            <div className="signup-page__connect-info">
              <h3 className="signup-page__connect-title">OneDrive</h3>
              <p className="signup-page__connect-description">
                Connect your Microsoft account to access files from OneDrive
              </p>
            </div>
            <button
              type="button"
              className={`signup-page__connect-btn ${microsoftConnected ? 'signup-page__connect-btn--connected' : ''}`}
              onClick={handleOneDriveConnect}
              disabled={microsoftConnected || connecting === 'google'}
            >
              {connecting === 'microsoft' ? (
                <>
                  <Loader2 className="signup-page__btn-spinner" size={16} />
                  Connecting…
                </>
              ) : microsoftConnected ? (
                <>
                  <Check size={16} />
                  Connected
                </>
              ) : (
                <>
                  Connect
                  <ArrowRight size={13} />
                </>
              )}
            </button>
          </div>
        </div>

        <button
          type="button"
          className="signup-page__continue-btn"
          onClick={handleContinue}
          disabled={!canContinue}
        >
          Continue to OmniDrive
          <ArrowRight size={13} />
        </button>

        <ProviderBadges />
      </main>

      <footer className="signup-page__footer">
        <span>&copy; 2026 OmniDrive</span>
        <span className="signup-page__version">v0.1 &middot; design preview</span>
      </footer>
    </div>
  )
}

export { AuthCallbackPage }