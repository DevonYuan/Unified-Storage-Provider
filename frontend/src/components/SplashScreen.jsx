import { useState, useEffect } from 'react'
import { HardDrive, Loader2 } from 'lucide-react'
import '../styles/SplashScreen.css'

const BACKEND_URL = 'http://127.0.0.1:8000'

export function SplashScreen({ onReady }) {
  const [status, setStatus] = useState('Starting OmniDrive...')
  const [dots, setDots] = useState('')

  // Animated dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.')
    }, 500)
    return () => clearInterval(interval)
  }, [])

  // Poll backend health
  useEffect(() => {
    let cancelled = false
    let attempts = 0

    async function check() {
      while (!cancelled && attempts < 30) {
        try {
          const res = await fetch(`${BACKEND_URL}/health`)
          if (res.ok) {
            if (!cancelled) {
              setStatus('Connected! Loading your workspace...')
              // Brief delay so user sees the transition
              setTimeout(() => {
                if (!cancelled) onReady()
              }, 600)
            }
            return
          }
        } catch {
          // Backend not ready yet
        }
        attempts++
        if (attempts === 5) setStatus('Waking up storage engines...')
        if (attempts === 15) setStatus('Almost ready...')
        await new Promise(r => setTimeout(r, 400))
      }
      // Timeout — proceed anyway, the app handles API errors
      if (!cancelled) onReady()
    }

    check()
    return () => { cancelled = true }
  }, [onReady])

  return (
    <div className="splash">
      <div className="splash__card">
        <div className="splash__logo">
          <HardDrive size={28} />
        </div>
        <h1 className="splash__title">OmniDrive</h1>
        <div className="splash__loader">
          <Loader2 size={18} className="splash__spinner" />
          <span className="splash__status">{status}{dots}</span>
        </div>
      </div>
    </div>
  )
}
