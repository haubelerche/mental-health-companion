import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, ChevronLeft, HeartPulse, Leaf, Lock, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { screeningService } from '../../services/screeningService'
import type { ScreeningInstrument, ScreeningId } from '../../services/screeningService'
import { ROUTE_PATHS } from '../../routes/paths'
import { toast } from 'react-toastify'

const STATIC_QUESTIONS: Record<ScreeningId, string[]> = {
  phq9: [
    'Ít hứng thú hoặc ít thấy vui trong các hoạt động',
    'Cảm thấy buồn, chán nản hoặc tuyệt vọng',
    'Khó ngủ, ngủ không ngon hoặc ngủ quá nhiều',
    'Cảm thấy mệt mỏi hoặc thiếu năng lượng',
    'Ăn không ngon miệng hoặc ăn quá nhiều',
    'Cảm thấy tồi về bản thân hoặc thất bại',
    'Khó tập trung vào mọi việc',
    'Di chuyển hoặc nói chuyện chậm bất thường',
    'Có ý nghĩ tự làm hại bản thân',
  ],
  gad7: [
    'Cảm thấy lo lắng, bất an hoặc căng thẳng',
    'Không thể ngừng hoặc kiểm soát được lo lắng',
    'Lo lắng quá mức về nhiều thứ khác nhau',
    'Khó thư giãn',
    'Bứt rứt đến mức khó ngồi yên',
    'Dễ khó chịu hoặc cáu kỉnh',
    'Cảm thấy sợ hãi như điều gì đó tồi tệ sắp xảy ra',
  ],
}

const LIKERT_OPTIONS = [
  { label: 'Không bao giờ', value: 0, short: 'Không' },
  { label: 'Vài ngày', value: 1, short: 'Vài ngày' },
  { label: 'Hơn nửa tháng', value: 2, short: 'Thường' },
  { label: 'Hầu hết mọi ngày', value: 3, short: 'Luôn luôn' },
] as const

const FALLBACK_INSTRUMENTS: ScreeningInstrument[] = [
  { id: 'phq9', title: 'Tâm trạng & Năng lượng', item_count: 9 },
  { id: 'gad7', title: 'Lo âu & Căng thẳng', item_count: 7 },
]

const INSTRUMENT_META: Record<ScreeningId, { icon: LucideIcon; desc: string; color: string; bg: string }> = {
  phq9: {
    icon: HeartPulse,
    desc: '9 câu · ~3 phút · Đánh giá mức độ trầm cảm',
    color: 'var(--color-may)',
    bg: 'var(--color-may-bg)',
  },
  gad7: {
    icon: Leaf,
    desc: '7 câu · ~2 phút · Đánh giá mức độ lo âu',
    color: 'var(--color-an)',
    bg: 'var(--color-an-bg)',
  },
}

// ── AnalyzingLoader ────────────────────────────────────────────────────────────
function AnalyzingLoader() {
  const steps = [
    'Đang đọc câu trả lời của bạn...',
    'Serene đang hiểu bạn hơn...',
    'Đang tổng hợp kết quả...',
  ]
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIdx((i) => Math.min(i + 1, steps.length - 1))
    }, 900)
    return () => clearInterval(interval)
  }, [steps.length])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-lua-bg rounded-4xl px-6">
      {/* Pulsing logo mark */}
      <motion.div
        animate={{ scale: [1, 1.12, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className="flex h-20 w-20 items-center justify-center rounded-3xl bg-serene-primary shadow-[0_12px_32px_rgba(77,99,89,0.3)]"
      >
        <Sparkles className="h-10 w-10 text-serene-accent" />
      </motion.div>

      {/* Step message */}
      <AnimatePresence mode="wait">
        <motion.p
          key={stepIdx}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          className="text-center font-display text-2xl text-serene-ink"
        >
          {steps[stepIdx]}
        </motion.p>
      </AnimatePresence>

      {/* Animated dots */}
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
            className="h-2.5 w-2.5 rounded-full bg-serene-primary"
          />
        ))}
      </div>

      <p className="text-sm text-serene-muted">Vui lòng đợi một chút...</p>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────
export function ScreeningFlow() {
  const navigate = useNavigate()
  const [instruments, setInstruments] = useState<ScreeningInstrument[]>([])
  const [selected, setSelected] = useState<ScreeningId | null>(null)
  const [currentQ, setCurrentQ] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [analyzing, setAnalyzing] = useState(false)
  const [direction, setDirection] = useState(1)

  useEffect(() => {
    screeningService.getCatalog()
      .then((d) => setInstruments(d.instruments))
      .catch(() => {
        if (import.meta.env.DEV) console.warn('[ScreeningFlow] catalog fetch failed')
      })
  }, [])

  const questions = selected ? (STATIC_QUESTIONS[selected] ?? []) : []
  const displayInstruments = instruments.length > 0 ? instruments : FALLBACK_INSTRUMENTS

  const pickAnswer = async (value: number) => {
    if (!selected) return
    const key = `q${currentQ}`
    const updated = { ...answers, [key]: value }
    setAnswers(updated)

    if (currentQ < questions.length - 1) {
      setDirection(1)
      setCurrentQ((q) => q + 1)
      return
    }

    // Last question — show analyzing loader then submit
    setAnalyzing(true)
    await new Promise((resolve) => setTimeout(resolve, 2800))
    try {
      const result = await screeningService.submit({
        instrument_id: selected,
        answers: updated,
      })
      navigate(ROUTE_PATHS.results, { state: { result } })
    } catch {
      toast.error('Không thể gửi kết quả. Thử lại nhé.')
      setAnalyzing(false)
    }
  }

  const goBack = () => {
    if (currentQ === 0) {
      setSelected(null)
      setAnswers({})
    } else {
      setDirection(-1)
      setCurrentQ((q) => q - 1)
    }
  }

  // Show analyzing loader
  if (analyzing) return <AnalyzingLoader />

  // ── Instrument selection ──────────────────────────────────────────────────
  if (!selected) {
    return (
      <div className="min-h-screen bg-lua-bg px-5 pt-10 pb-28 rounded-4xl">
        <p className="mb-1 text-[10px] uppercase tracking-widest text-serene-muted">Sàng lọc</p>
        <h1 className="mb-2 font-display text-3xl text-serene-ink leading-snug">
          Chọn chủ đề sàng lọc
        </h1>
        <p className="mb-8 text-sm text-serene-muted">
          Bài test ngắn — kết quả hiển thị dễ hiểu, không dùng ngôn ngữ lâm sàng.
        </p>

        <div className="flex flex-col gap-4">
          {displayInstruments.map((inst, i) => {
            const meta = INSTRUMENT_META[inst.id as ScreeningId]
            const InstIcon = meta?.icon ?? Brain
            return (
              <motion.button
                key={inst.id}
                type="button"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                onClick={() => setSelected(inst.id)}
                className="flex items-center gap-4 rounded-3xl bg-white p-5 text-left shadow-sm transition hover:shadow-md active:scale-[0.98]"
              >
                <div
                  className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl text-[var(--color-serene-primary)]"
                  style={{ backgroundColor: meta?.bg ?? '#f3f5f2' }}
                >
                  <InstIcon className="h-7 w-7" aria-hidden />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-serene-ink">{inst.title}</div>
                  <div className="mt-0.5 text-sm text-serene-muted">
                    {meta?.desc ?? `${inst.item_count} câu`}
                  </div>
                </div>
                <ChevronLeft className="h-5 w-5 rotate-180 text-serene-muted" />
              </motion.button>
            )
          })}
        </div>

        {/* Disclaimer */}
        <div className="mt-8 rounded-2xl border border-serene-border bg-white/60 p-4">
          <p className="flex items-start gap-2 text-xs leading-relaxed text-serene-muted">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-serene-primary/70" aria-hidden />
            <span>Kết quả chỉ dùng để gợi ý hỗ trợ — không phải chẩn đoán lâm sàng. Serene không lưu thông tin nhận dạng.</span>
          </p>
        </div>
      </div>
    )
  }

  // Guard: no questions
  if (questions.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-lua-bg)] p-6">
        <div className="text-center">
          <p className="mb-4 text-serene-muted">Không thể tải câu hỏi.</p>
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="font-medium text-sm text-serene-primary"
          >
            Chọn lại
          </button>
        </div>
      </div>
    )
  }

  const progress = ((currentQ + 1) / questions.length) * 100

  // ── Questionnaire ────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen flex-col bg-lua-bg rounded-4xl px-5 pb-28 pt-8">
      {/* Header + progress */}
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-3">
          <button
            type="button"
            onClick={goBack}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-serene-border bg-white/70 text-serene-muted transition hover:bg-white"
            aria-label="Quay lại"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <div className="h-1.5 overflow-hidden rounded-full bg-serene-border/60">
              <motion.div
                className="h-full rounded-full bg-serene-primary"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </div>
          </div>
          <span className="min-w-[36px] text-right text-xs font-medium text-serene-muted">
            {currentQ + 1}/{questions.length}
          </span>
        </div>
      </div>

      {/* Question card */}
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={currentQ}
          custom={direction}
          variants={{
            enter: (d: number) => ({ x: d > 0 ? 40 : -40, opacity: 0 }),
            center: { x: 0, opacity: 1 },
            exit: (d: number) => ({ x: d > 0 ? -40 : 40, opacity: 0 }),
          }}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          className="flex flex-1 flex-col"
        >
          <p className="mb-2 text-[11px] uppercase tracking-widest text-serene-muted">
            Trong 2 tuần qua, bạn có thường xuyên bị phiền bởi:
          </p>
          <h2 className="mb-8 font-display text-2xl leading-snug text-serene-ink">
            "{questions[currentQ]}"?
          </h2>

          {/* Likert pills */}
          <div className="space-y-3">
            {LIKERT_OPTIONS.map((opt) => (
              <motion.button
                key={opt.value}
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => pickAnswer(opt.value)}
                className="group flex w-full items-center justify-between rounded-2xl border border-serene-border bg-white px-5 py-4 text-left shadow-sm transition-all hover:border-serene-primary/50 hover:bg-serene-primary/5 hover:shadow-md active:scale-[0.98]"
              >
                <div className="flex items-center gap-3">
                  {/* Frequency dot indicator */}
                  <div className="flex gap-1">
                    {[0, 1, 2, 3].map((i) => (
                      <span
                        key={i}
                        className={`h-2 w-2 rounded-full transition-colors ${
                          i <= opt.value ? 'bg-serene-primary' : 'bg-serene-border'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="font-medium text-serene-ink">{opt.label}</span>
                </div>
                <span className="text-xs text-serene-muted group-hover:text-serene-primary">
                  {opt.short}
                </span>
              </motion.button>
            ))}
          </div>

          {/* Pause link */}
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.home)}
            className="mt-8 text-center text-xs text-serene-muted transition hover:text-serene-ink"
          >
            Nghỉ một chút — tiếp tục sau
          </button>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
