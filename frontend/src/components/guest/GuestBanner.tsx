import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function GuestBanner() {
  const { guestSession } = useAuth()
  const navigate = useNavigate()
  const [secondsLeft, setSecondsLeft] = useState(0)

  useEffect(() => {
    if (!guestSession) return
    const tick = () => {
      const diff = Math.max(0, Math.floor((guestSession.expiresAt - Date.now()) / 1000))
      setSecondsLeft(diff)
      if (diff === 0) navigate('/register')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [guestSession, navigate])

  if (!guestSession) return null

  const mins = Math.floor(secondsLeft / 60)
  const secs = secondsLeft % 60

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-2 bg-[var(--color-serene-primary)] text-[var(--color-serene-on-primary)] text-sm font-medium shadow-md">
      <span>
        Dùng thử — còn{' '}
        <span className="font-bold tabular-nums">
          {mins}:{String(secs).padStart(2, '0')}
        </span>
      </span>
      <button
        onClick={() => navigate('/register')}
        className="rounded-full bg-white/20 hover:bg-white/30 px-3 py-0.5 text-xs transition-all"
      >
        Lưu hành trình →
      </button>
    </div>
  )
}
