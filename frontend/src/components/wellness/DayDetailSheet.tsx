import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export type DayDetail = {
  date: string          // YYYY-MM-DD
  score: number         // 0–100
  label?: string        // mood label text
  wordChips?: string[]  // emotion words logged that day
  note?: string         // journal note if any
}

type Props = {
  detail: DayDetail | null
  onClose: () => void
}

function scoreToEmoji(score: number): string {
  if (score >= 80) return '😊'
  if (score >= 60) return '😌'
  if (score >= 40) return '😐'
  if (score >= 20) return '😔'
  return '😟'
}

function scoreToLabel(score: number): string {
  if (score >= 80) return 'Rất tốt'
  if (score >= 60) return 'Khá ổn'
  if (score >= 40) return 'Bình thường'
  if (score >= 20) return 'Hơi thấp'
  return 'Khó khăn'
}

function scoreToColor(score: number): string {
  if (score >= 80) return '#15803d'
  if (score >= 60) return '#16a34a'
  if (score >= 40) return '#ca8a04'
  if (score >= 20) return '#ea580c'
  return '#dc2626'
}

function formatDisplayDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('vi-VN', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

export function DayDetailSheet({ detail, onClose }: Props) {
  return (
    <AnimatePresence>
      {detail && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-serene-ink/30 backdrop-blur-[2px]"
          />

          {/* Bottom sheet */}
          <motion.div
            key="sheet"
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: 'spring', stiffness: 340, damping: 32 }}
            className="fixed bottom-0 left-0 right-0 z-50 mx-auto max-w-lg rounded-t-3xl bg-white px-6 pb-10 pt-5 shadow-[0_-8px_40px_rgba(47,52,46,0.18)]"
          >
            {/* Drag handle */}
            <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-serene-border" />

            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="absolute right-5 top-5 flex h-8 w-8 items-center justify-center rounded-full text-serene-muted hover:bg-serene-border/40"
              aria-label="Đóng"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Date */}
            <p className="text-[11px] font-semibold uppercase tracking-widest text-serene-muted">
              {formatDisplayDate(detail.date)}
            </p>

            {/* Mood headline */}
            <div className="mt-3 flex items-center gap-4">
              <motion.span
                initial={{ scale: 0.5 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 18 }}
                className="text-5xl"
              >
                {scoreToEmoji(detail.score)}
              </motion.span>
              <div>
                <p
                  className="font-display text-3xl"
                  style={{ color: scoreToColor(detail.score) }}
                >
                  {detail.label || scoreToLabel(detail.score)}
                </p>
                <p className="mt-0.5 text-sm text-serene-muted">
                  Wellness score: {Math.round(detail.score)}%
                </p>
              </div>
            </div>

            {/* Score bar */}
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-serene-border/50">
              <motion.div
                className="h-full rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${detail.score}%` }}
                transition={{ duration: 0.6, ease: 'easeOut', delay: 0.15 }}
                style={{ backgroundColor: scoreToColor(detail.score) }}
              />
            </div>

            {/* Word chips */}
            {detail.wordChips && detail.wordChips.length > 0 && (
              <div className="mt-5">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-serene-muted">
                  Cảm xúc ghi nhận
                </p>
                <div className="flex flex-wrap gap-2">
                  {detail.wordChips.map((chip) => (
                    <span
                      key={chip}
                      className="rounded-full border border-serene-border bg-serene-surface-2 px-3 py-1 text-sm text-serene-ink"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Note */}
            {detail.note && (
              <div className="mt-5 rounded-2xl bg-serene-surface-2 p-4">
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-serene-muted">
                  Ghi chú
                </p>
                <p className="text-sm leading-relaxed text-serene-ink">{detail.note}</p>
              </div>
            )}

            {/* Empty state */}
            {!detail.wordChips?.length && !detail.note && (
              <p className="mt-5 text-sm text-serene-muted">
                Không có ghi chú chi tiết cho ngày này.
              </p>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
