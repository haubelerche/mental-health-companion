import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { safetyService } from '../../services/safetyService'
import { ROUTE_PATHS } from '../../routes/paths'

const QUESTIONS = [
  { key: 'overwhelmed' as const, text: 'Bạn có đang cảm thấy quá tải không?' },
  { key: 'unsafe' as const, text: 'Bạn có đang cảm thấy không an toàn không?' },
  { key: 'need_help_now' as const, text: 'Bạn có cần được hỗ trợ ngay không?' },
]

type Answers = Record<'overwhelmed' | 'unsafe' | 'need_help_now', string>

export function SafetyCheck() {
  const navigate = useNavigate()
  const location = useLocation()
  const nextPath: string = (location.state as { next?: string } | null)?.next ?? ROUTE_PATHS.chat

  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Answers>({
    overwhelmed: 'Không',
    unsafe: 'Không',
    need_help_now: 'Không',
  })
  const [loading, setLoading] = useState(false)

  const q = QUESTIONS[step]

  const handleAnswer = async (value: 'Có' | 'Không') => {
    const updated: Answers = { ...answers, [q.key]: value }
    setAnswers(updated)

    if (step < QUESTIONS.length - 1) {
      setStep(s => s + 1)
      return
    }

    // Last question answered — call safety check API
    setLoading(true)
    try {
      const result = await safetyService.check(updated)
      if (result.should_route_crisis) {
        navigate(ROUTE_PATHS.chat, { state: { crisisMode: true } })
      } else {
        navigate(nextPath)
      }
    } catch {
      // On error, proceed to intended destination (fail open — not crisis by default)
      navigate(nextPath)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-serene-bg)] flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm">
        {/* Progress bar */}
        <div className="flex gap-2 mb-12">
          {QUESTIONS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                i <= step
                  ? 'bg-[var(--color-serene-primary)]'
                  : 'bg-[var(--color-serene-outline)]'
              }`}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <p className="text-[10px] text-[var(--color-serene-muted)] mb-3 uppercase tracking-widest">
              Câu {step + 1} / {QUESTIONS.length}
            </p>
            <h2 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-10 leading-snug">
              {q.text}
            </h2>

            <div className="flex flex-col gap-3">
              {(['Không', 'Có'] as const).map(opt => (
                <button
                  key={opt}
                  type="button"
                  disabled={loading}
                  onClick={() => handleAnswer(opt)}
                  className={`w-full py-4 rounded-2xl font-semibold text-sm transition-all active:scale-[0.97] disabled:opacity-50 ${
                    opt === 'Không'
                      ? 'bg-[var(--color-serene-surface)] text-[var(--color-serene-ink)] hover:bg-[var(--color-serene-accent)]'
                      : 'bg-[var(--color-serene-primary)] text-[var(--color-serene-on-primary)] hover:bg-[var(--color-serene-primary-dim)]'
                  }`}
                >
                  {loading && opt === 'Có' ? 'Đang xử lý…' : opt}
                </button>
              ))}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
