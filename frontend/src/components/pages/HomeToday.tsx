import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../../hooks/useAuth'
import { homeService, type HomeFeed } from '../../services/homeService'
import { ROUTE_PATHS } from '../../routes/paths'

const PERSONAS = [
  {
    id: 'checkin',
    label: 'Check-in nhanh',
    sub: 'An · 2 phút',
    emoji: '☀️',
    bg: 'var(--color-an-bg)',
    accent: 'var(--color-an)',
    next: ROUTE_PATHS.checkin,
  },
  {
    id: 'screening',
    label: 'Làm bài sàng lọc',
    sub: 'Lửa · ~5 phút',
    emoji: '📋',
    bg: 'var(--color-lua-bg)',
    accent: 'var(--color-lua)',
    next: ROUTE_PATHS.screening,
  },
  {
    id: 'chat',
    label: 'Trò chuyện ngay',
    sub: 'Mây · luôn sẵn',
    emoji: '💬',
    bg: 'var(--color-may-bg)',
    accent: 'var(--color-may)',
    next: ROUTE_PATHS.chat,
  },
]

export function HomeToday() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [feed, setFeed] = useState<HomeFeed | null>(null)

  useEffect(() => {
    homeService.feed()
      .then(setFeed)
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('[HomeToday] feed fetch failed', err)
      })
  }, [])

  // All 3 CTAs route through safety check first, carrying next destination
  const handleChoice = (next: string) => {
    navigate('/serene/safety-check', { state: { next } })
  }

  const firstName = user?.displayName?.split(' ').slice(-1)[0] ?? ''

  return (
    <div className="min-h-screen bg-[var(--color-serene-bg)] px-5 pt-8 pb-28">
      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-2"
      >
        <p className="text-[var(--color-serene-muted)] text-sm">
          {new Date().toLocaleDateString('vi-VN', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </p>
        <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)] mt-1 leading-snug">
          Hôm nay bạn muốn gì{firstName ? `, ${firstName}` : ''}?
        </h1>
      </motion.div>

      {/* Quote */}
      {feed?.quote_of_day && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="text-sm italic text-[var(--color-serene-muted)] my-4 leading-relaxed border-l-2 border-[var(--color-serene-outline)] pl-3"
        >
          "{feed.quote_of_day.text}"
          {feed.quote_of_day.author && (
            <span className="not-italic ml-1">— {feed.quote_of_day.author}</span>
          )}
        </motion.p>
      )}

      {/* Today's mood badge */}
      {feed?.mood_today && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="mb-6 inline-flex items-center gap-2 bg-[var(--color-serene-surface)] rounded-full px-4 py-1.5 text-sm text-[var(--color-serene-muted)]"
        >
          <span>{feed.mood_today.emoji ?? '😌'}</span>
          <span>
            Hôm nay cảm thấy{' '}
            <strong className="text-[var(--color-serene-ink)]">{feed.mood_today.mood}</strong>
          </span>
        </motion.div>
      )}

      {/* 3 Persona CTAs */}
      <div className="flex flex-col gap-4">
        {PERSONAS.map((p, i) => (
          <motion.button
            key={p.id}
            type="button"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 + i * 0.08 }}
            onClick={() => handleChoice(p.next)}
            className="w-full text-left rounded-3xl p-5 flex items-center gap-4 shadow-sm hover:shadow-md active:scale-[0.98] transition-all duration-150"
            style={{ backgroundColor: p.bg }}
          >
            <div
              aria-hidden="true"
              className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
              style={{ backgroundColor: p.accent + '44' }}
            >
              {p.emoji}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[var(--color-serene-ink)] text-base leading-tight">
                {p.label}
              </div>
              <div className="text-sm text-[var(--color-serene-muted)] mt-0.5">{p.sub}</div>
            </div>
            <span aria-hidden="true" className="text-[var(--color-serene-muted)] text-xl flex-shrink-0">›</span>
          </motion.button>
        ))}
      </div>

      {/* Dynamic suggestion */}
      {feed?.dynamic_suggestion && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-6 p-4 bg-[var(--color-serene-surface)] rounded-2xl text-sm text-[var(--color-serene-muted)] leading-relaxed"
        >
          💡 {feed.dynamic_suggestion.message}
        </motion.div>
      )}
    </div>
  )
}
