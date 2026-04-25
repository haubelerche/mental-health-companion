import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AirVent, Cloud, Leaf, Sparkles } from 'lucide-react'
import { toast } from 'react-toastify'
import { useAuth } from '../../hooks/useAuth'
import { homeService, type HomeFeed } from '../../services/homeService'
import { ROUTE_PATHS } from '../../routes/paths'

const MOODS = [
  { icon: Leaf,     title: 'Check-in Cảm xúc', desc: 'Ghi nhận nhanh trạng thái hiện tại.', apiMood: 'neutral',     emoji: '🍃' },
  { icon: Cloud,    title: 'Ủ rũ',  desc: 'Để mọi thứ trở nên dễ chịu hơn.',  apiMood: 'melancholic', emoji: '☁️' },
  { icon: Sparkles, title: 'Rạng rỡ',  desc: 'Năng lượng đang mở ra.',        apiMood: 'bright',     emoji: '✨' },
  { icon: AirVent,  title: 'Bồn chồn', desc: 'Cần một nhịp thở sâu.',         apiMood: 'restless',   emoji: '🌬️' },
] as const

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
  const [checkedInMood, setCheckedInMood] = useState<string | null>(null)
  const [submittingMood, setSubmittingMood] = useState<string | null>(null)

  useEffect(() => {
    homeService.feed()
      .then((data) => {
        setFeed(data)
        setCheckedInMood(data.mood_today.mood)
      })
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('[HomeToday] feed fetch failed', err)
      })
  }, [])

  const moodCards = useMemo(
    () => MOODS.map((m) => ({ ...m, active: checkedInMood === m.apiMood })),
    [checkedInMood],
  )

  const onCheckinMood = async (apiMood: string, emoji: string) => {
    if (submittingMood) return
    try {
      setSubmittingMood(apiMood)
      await homeService.checkin({ mood: apiMood, emoji })
      setCheckedInMood(apiMood)
      toast.success('Đã lưu mood check-in hôm nay.')
    } catch (err) {
      toast.info(err instanceof Error ? err.message : 'Không thể lưu check-in')
    } finally {
      setSubmittingMood(null)
    }
  }

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

      {/* Mood picker */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="grid grid-cols-2 gap-3 mb-6"
      >
        {moodCards.map((mood) => {
          const Icon = mood.icon
          return (
            <button
              key={mood.apiMood}
              type="button"
              aria-busy={submittingMood === mood.apiMood}
              disabled={submittingMood !== null}
              onClick={() => void onCheckinMood(mood.apiMood, mood.emoji)}
              className={[
                'rounded-[22px] border px-4 py-5 text-left transition-all active:scale-[0.97] disabled:opacity-60',
                mood.active
                  ? 'border-[var(--color-serene-primary)]/20 bg-[var(--color-serene-primary)] text-[var(--color-serene-on-primary)] shadow-md'
                  : 'border-white/45 bg-white/70 hover:bg-white/90',
              ].join(' ')}
            >
              <Icon className={['h-6 w-6', mood.active ? 'text-[var(--color-serene-accent)]' : 'text-[var(--color-serene-primary)]'].join(' ')} aria-hidden="true" />
              <p className={['mt-4 font-semibold text-base', mood.active ? 'text-[var(--color-serene-on-primary)]' : 'text-[var(--color-serene-ink)]'].join(' ')}>
                {mood.title}
              </p>
              <p className={['mt-1 text-xs leading-snug', mood.active ? 'text-[var(--color-serene-on-primary)]/75' : 'text-[var(--color-serene-muted)]'].join(' ')}>
                {mood.desc}
              </p>
            </button>
          )
        })}
      </motion.div>

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
