import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
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

const OPTIONS = [
  { label: 'Không bao giờ', value: 0 },
  { label: 'Vài ngày', value: 1 },
  { label: 'Hơn một nửa số ngày', value: 2 },
  { label: 'Hầu hết mọi ngày', value: 3 },
] as const

const FALLBACK_INSTRUMENTS: ScreeningInstrument[] = [
  { id: 'phq9', title: 'Tâm trạng & Năng lượng', item_count: 9 },
  { id: 'gad7', title: 'Lo âu & Căng thẳng', item_count: 7 },
]

export function ScreeningFlow() {
  const navigate = useNavigate()
  const [instruments, setInstruments] = useState<ScreeningInstrument[]>([])
  const [selected, setSelected] = useState<ScreeningId | null>(null)
  const [currentQ, setCurrentQ] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    screeningService.getCatalog()
      .then(d => setInstruments(d.instruments))
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
      setCurrentQ(q => q + 1)
      return
    }

    setLoading(true)
    try {
      const result = await screeningService.submit({
        instrument_id: selected,
        answers: updated,
      })
      navigate(ROUTE_PATHS.results, { state: { result } })
    } catch {
      toast.error('Không thể gửi kết quả. Thử lại nhé.')
    } finally {
      setLoading(false)
    }
  }

  // Instrument selection screen
  if (!selected) {
    return (
      <div className="min-h-screen bg-[var(--color-lua-bg)] px-5 pt-10 pb-28">
        <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">
          Lửa · Sàng lọc
        </p>
        <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)] mb-2 leading-snug">
          Chọn chủ đề sàng lọc
        </h1>
        <p className="text-sm text-[var(--color-serene-muted)] mb-8">
          Bài test ngắn — kết quả hiển thị dễ hiểu, không có ngôn ngữ lâm sàn.
        </p>
        <div className="flex flex-col gap-4">
          {displayInstruments.map((inst, i) => (
            <motion.button
              key={inst.id}
              type="button"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              onClick={() => setSelected(inst.id)}
              className="bg-white rounded-3xl p-5 text-left shadow-sm hover:shadow-md active:scale-[0.98] transition-all"
            >
              <div className="font-semibold text-[var(--color-serene-ink)] text-lg">{inst.title}</div>
              <div className="text-sm text-[var(--color-serene-muted)] mt-1">
                {inst.id === 'phq9' ? '9' : '7'} câu · ~3 phút
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    )
  }

  // Questionnaire screen
  return (
    <div className="min-h-screen bg-[var(--color-lua-bg)] px-5 pt-10 pb-28">
      {/* Progress bar */}
      <div className="h-1 bg-[var(--color-serene-outline)] rounded-full mb-10 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: 'var(--color-lua)' }}
          animate={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
          transition={{ duration: 0.28 }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentQ}
          initial={{ opacity: 0, x: 28 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -28 }}
          transition={{ duration: 0.18 }}
        >
          <p className="text-[10px] text-[var(--color-serene-muted)] mb-2 uppercase tracking-widest">
            {currentQ + 1} / {questions.length}
          </p>
          <p className="text-sm text-[var(--color-serene-muted)] mb-2">
            Trong 2 tuần qua, bạn có thường xuyên bị phiền bởi:
          </p>
          <h2 className="font-[var(--font-display)] text-xl text-[var(--color-serene-ink)] mb-10 leading-snug">
            "{questions[currentQ]}"?
          </h2>

          <div className="flex flex-col gap-3">
            {OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                disabled={loading}
                onClick={() => pickAnswer(opt.value)}
                className="w-full bg-white rounded-2xl p-4 text-left font-medium text-[var(--color-serene-ink)] shadow-sm hover:shadow-md active:scale-[0.98] transition-all disabled:opacity-50 text-sm"
              >
                {opt.label}
              </button>
            ))}
          </div>

          {loading && (
            <p className="text-center text-xs text-[var(--color-serene-muted)] mt-4 animate-pulse">
              Đang gửi kết quả…
            </p>
          )}

          {/* Pause button */}
          <button
            type="button"
            onClick={() => navigate(ROUTE_PATHS.home)}
            className="w-full text-center text-xs text-[var(--color-serene-muted)] mt-6 hover:text-[var(--color-serene-ink)] transition"
          >
            Nghỉ một chút — lưu tiến độ sau
          </button>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
