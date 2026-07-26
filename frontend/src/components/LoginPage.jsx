import { useAuth } from '../context/AuthContext.jsx'
import { LogOut, HardDrive } from 'lucide-react'

const C = {
  bg: '#080808',
  surface: '#111111',
  border: '#1f1f1f',
  fg: '#f5f5f5',
  fgMuted: '#888888',
  fgSubtle: '#444444',
  accent: '#4ade80',
  accentBlue: '#60a5fa',
}

function ArcBackground() {
  return (
    <div
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}
    >
      <svg
        style={{ position: 'absolute', top: -400, right: -400, width: 900, height: 900, opacity: 0.055 }}
        viewBox="0 0 900 900"
        fill="none"
      >
        <circle cx="450" cy="450" r="390" stroke="white" strokeWidth="1.2" />
        <circle cx="450" cy="450" r="310" stroke="white" strokeWidth="0.9" />
        <circle cx="450" cy="450" r="230" stroke="white" strokeWidth="0.6" />
      </svg>
      <svg
        style={{ position: 'absolute', bottom: -280, left: -180, width: 580, height: 580, opacity: 0.03 }}
        viewBox="0 0 580 580"
        fill="none"
      >
        <circle cx="290" cy="290" r="240" stroke="white" strokeWidth="1" />
        <circle cx="290" cy="290" r="170" stroke="white" strokeWidth="0.7" />
      </svg>
    </div>
  )
}

function ProviderBadges() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
      <span style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: C.fgSubtle }}>
        Works with
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, letterSpacing: '0.05em', textTransform: 'uppercase', color: C.fgMuted }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: C.accent, display: 'inline-block' }} />
        Google Drive
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, letterSpacing: '0.05em', textTransform: 'uppercase', color: C.fgMuted }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: C.accentBlue, display: 'inline-block' }} />
        OneDrive
      </span>
    </div>
  )
}

export function LoginPage() {
  const { user, isLoading, login, logout } = useAuth()

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: C.bg }}>
        <span style={{ fontSize: 13, color: C.fgMuted }}>Loading...</span>
      </div>
    )
  }

  if (user) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: C.bg, display: 'flex', flexDirection: 'column' }}>
        <header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 32px', borderBottom: `1px solid ${C.border}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, backgroundColor: C.surface, border: `1px solid ${C.border}`,
              borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <HardDrive size={13} color={C.fgMuted} />
            </div>
            <span style={{ fontSize: 13, fontWeight: 500, color: C.fg }}>OmniDrive</span>
          </div>
          <button
            onClick={logout}
            style={{
              display: 'flex', alignItems: 'center', gap: 7,
              fontSize: 13, color: C.fgMuted, background: 'none', border: 'none',
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={e => (e.currentTarget.style.color = C.fg)}
            onMouseLeave={e => (e.currentTarget.style.color = C.fgMuted)}
          >
            <LogOut size={14} />
            Sign out
          </button>
        </header>
        <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
          <div style={{ textAlign: 'center', maxWidth: 360 }}>
            <p style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: C.fgSubtle, marginBottom: 12 }}>
              Signed in
            </p>
            <h2 style={{ fontSize: 28, fontWeight: 600, color: C.fg, marginBottom: 12, lineHeight: 1.2 }}>
              Welcome back.
            </h2>
            <p style={{ fontSize: 14, color: C.fgMuted, lineHeight: 1.6, marginBottom: 16 }}>
              Your unified cloud storage workspace is on its way. Connect your providers to get started.
            </p>
            <p style={{ fontSize: 11, color: C.fgSubtle, fontFamily: "'Geist Mono', monospace", marginTop: 8 }}>
              {user.id}
            </p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div style={{ position: 'relative', minHeight: '100vh', backgroundColor: C.bg, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <ArcBackground />

      <nav style={{
        position: 'relative', zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '20px 32px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28, height: 28, backgroundColor: C.surface, border: `1px solid ${C.border}`,
            borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <HardDrive size={13} color={C.fgMuted} />
          </div>
          <span style={{ fontSize: 13, fontWeight: 500, color: C.fg }}>OmniDrive</span>
        </div>
      </nav>

      <main style={{
        position: 'relative', zIndex: 10,
        flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '16px 32px 48px', maxWidth: 760,
      }}>
        <div style={{ marginBottom: 32 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            fontSize: 12, color: C.fgMuted,
            border: `1px solid ${C.border}`, borderRadius: 999,
            padding: '6px 14px',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: C.accent, display: 'inline-block' }} />
            One storage layer. All your clouds underneath.
          </span>
        </div>

        <h1 style={{ fontSize: 60, fontWeight: 700, lineHeight: 1.05, letterSpacing: '-0.03em', marginBottom: 24 }}>
          <span style={{ color: C.fg, display: 'block' }}>Multiple clouds.</span>
          <span style={{ color: C.fgMuted, display: 'block' }}>All in one place.</span>
        </h1>

        <p style={{ fontSize: 15, color: C.fgMuted, lineHeight: 1.65, maxWidth: 460, marginBottom: 40 }}>
          OmniDrive unifies Google Drive and OneDrive into a single, quiet
          workspace. No more switching tabs or guessing where a file lives.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
          <button
            onClick={login}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              backgroundColor: C.fg, color: C.bg,
              fontSize: 13, fontWeight: 500,
              padding: '10px 20px', borderRadius: 999, border: 'none',
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.88')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Open OmniDrive
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
              <path d="M2 6.5H11M11 6.5L7.5 3M11 6.5L7.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        <ProviderBadges />
      </main>

      <footer style={{
        position: 'relative', zIndex: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 32px', fontSize: 11, color: C.fgSubtle,
      }}>
        <span>&copy; 2026 OmniDrive</span>
        <span style={{ fontFamily: "'Geist Mono', monospace" }}>v0.1 &middot; design preview</span>
      </footer>
    </div>
  )
}
