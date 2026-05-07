import { motion, AnimatePresence } from 'framer-motion'
import { Check, Heart, Sprout, X, Flame } from 'lucide-react'

type Props = {
  open: boolean
  streakDays: number
  heartsEarned?: number
  completedDays?: number[]  // 0=Sun to 6=Sat indices
  onClose: () => void
  onClaim?: () => void
}

const WEEKDAYS = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']

function getTodayIndex(): number {
  return new Date().getDay() // 0=Sun
}

export function StreakCelebration({
  open,
  streakDays,
  heartsEarned = 10,
  completedDays,
  onClose,
  onClaim,
}: Props) {
  const today = getTodayIndex()
  // Default: mark today and recent days based on streak
  const done = completedDays ?? Array.from({ length: Math.min(streakDays, 7) }, (_, i) => (today - i + 7) % 7)

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-serene-ink/40 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.85, y: 40 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', stiffness: 280, damping: 26 }}
            className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-40px)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-3xl bg-white p-7 shadow-2xl"
          >
            {/* Close */}
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-serene-muted transition hover:bg-serene-border/40"
              aria-label="Đóng"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Icon */}
            <div className="mb-5 text-center">
              <motion.div
                animate={{ rotate: [0, -12, 12, -8, 8, 0] }}
                transition={{ duration: 0.7, delay: 0.2 }}
                className="inline-flex h-20 w-20 items-center justify-center rounded-3xl bg-amber-50"
              >
                <Flame className="h-10 w-10 text-amber-500" />
              </motion.div>
            </div>

            {/* Headline */}
            <div className="mb-6 text-center">
              <h2 className="font-display text-3xl text-serene-ink">Xuất sắc!</h2>
              <p className="mt-1.5 text-lg font-semibold text-amber-500">
                {streakDays} ngày liên tiếp
              </p>
              <p className="mt-2 text-sm text-serene-muted">
                Bạn đã check-in đều đặn — hãy tiếp tục nhé!
              </p>
            </div>

            {/* Weekly dots S M T W T F S */}
            <div className="mb-6 flex items-center justify-between gap-1">
              {WEEKDAYS.map((day, idx) => {
                const isDone = done.includes(idx)
                const isToday = idx === today
                return (
                  <div key={day} className="flex flex-col items-center gap-1.5">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: idx * 0.06 + 0.3, type: 'spring', stiffness: 300 }}
                      className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                        isDone
                          ? 'bg-amber-400 text-white shadow-sm shadow-amber-200'
                          : isToday
                            ? 'border-2 border-serene-primary bg-serene-primary/10 text-serene-primary'
                            : 'bg-serene-border/50 text-serene-muted'
                      }`}
                    >
                      {isDone ? <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden /> : day.charAt(0)}
                    </motion.div>
                    <span className={`text-[10px] font-medium ${isToday ? 'text-serene-primary' : 'text-serene-muted'}`}>
                      {day}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Hearts earned */}
            <div className="mb-5 flex items-center justify-center gap-2 rounded-2xl bg-rose-50 py-3">
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.3, 1] }}
                transition={{ delay: 0.5, duration: 0.4 }}
                className="inline-flex text-rose-500"
              >
                <Heart className="h-6 w-6 fill-rose-400/30" aria-hidden />
              </motion.span>
              <p className="font-semibold text-rose-500">+{heartsEarned} tim nhận được!</p>
            </div>

            {/* CTA */}
            <button
              type="button"
              onClick={onClaim ?? onClose}
              className="w-full rounded-full bg-serene-primary py-3.5 font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 active:scale-[0.97]"
            >
              <span className="inline-flex items-center justify-center gap-2">
                <Sprout className="h-4 w-4" aria-hidden />
                Nhận phần thưởng
              </span>
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
