import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { checkinService } from '../../services/checkinService'
import { ROUTE_PATHS } from '../../routes/paths'
import { toast } from 'react-toastify'

type Step = 'mood' | 'sliders' | 'note' | 'summary'

const MOODS = [
  { label: 'Rất tệ', emoji: '😞', value: 'rat_te' },
  { label: 'Không ổn', emoji: '😕', value: 'khong_on' },
  { label: 'Bình thường', emoji: '😐', value: 'binh_thuong' },
  { label: 'Khá ổn', emoji: '🙂', value: 'kha_on' },
  { label: 'Tuyệt vời', emoji: '😄', value: 'tuyet_voi' },
] as const

type Mood = typeof MOODS[number]

export function CheckinFlow() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('mood')
  const [mood, setMood] = useState<Mood | null>(null)
  const [stress, setStress] = useState(5)
  const [sleep, setSleep] = useState(7)
  const [study, setStudy] = useState(4)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)

  const pickMood = (m: Mood) => {
    setMood(m)
    setStep('sliders')
  }

  const sliders = useMemo(() => [
    { label: 'Mức căng thẳng', value: stress, setter: setStress, min: 0, max: 10, step: 1, unit: '/ 10' },
    { label: 'Giờ ngủ tối qua', value: sleep, setter: setSleep, min: 0, max: 12, step: 0.5, unit: 'giờ' },
    { label: 'Giờ học / làm', value: study, setter: setStudy, min: 0, max: 16, step: 0.5, unit: 'giờ' },
  ], [stress, sleep, study])

  const submit = async () => {
    if (!mood) return
    setLoading(true)
    try {
      await checkinService.quickCheckin({
        mood: mood.value,
        stress_level: stress,
        sleep_hours: sleep,
        study_hours: study,
        note: note.trim() || null,
      })
      setStep('summary')
    } catch {
      toast.error('Không thể lưu check-in. Thử lại nhé.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-an-bg)] px-5 pt-10 pb-28">
      <AnimatePresence mode="wait">

        {step === 'mood' && (
          <motion.div key="mood" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">
              An · Check-in
            </p>
            <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)] mb-8 leading-snug">
              Hôm nay bạn đang cảm thấy thế nào?
            </h1>
            <div className="flex flex-col gap-3">
              {MOODS.map(m => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => pickMood(m)}
                  className="flex items-center gap-4 bg-white rounded-2xl p-4 shadow-sm hover:shadow-md active:scale-[0.98] transition-all text-left"
                >
                  <span className="text-3xl" aria-hidden="true">{m.emoji}</span>
                  <span className="font-medium text-[var(--color-serene-ink)]">{m.label}</span>
                  <span className="ml-auto text-[var(--color-serene-muted)]" aria-hidden="true">›</span>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {step === 'sliders' && (
          <motion.div key="sliders" initial={{ opacity: 0, x: 28 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">
              An · Check-in
            </p>
            <h1 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-8 leading-snug">
              Vài con số hôm nay
            </h1>

            {sliders.map(s => (
              <div key={s.label} className="mb-7">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[var(--color-serene-ink)] font-medium">{s.label}</span>
                  <span className="text-[var(--color-serene-muted)] tabular-nums">{s.value} {s.unit}</span>
                </div>
                <input
                  type="range"
                  min={s.min}
                  max={s.max}
                  step={s.step}
                  value={s.value}
                  onChange={e => s.setter(parseFloat(e.target.value))}
                  className="w-full accent-[var(--color-an)]"
                  aria-label={s.label}
                />
              </div>
            ))}

            <button
              type="button"
              onClick={() => setStep('note')}
              className="w-full bg-[var(--color-serene-primary)] hover:bg-[var(--color-serene-primary-dim)] text-[var(--color-serene-on-primary)] py-3.5 rounded-2xl font-semibold text-sm transition-all mt-2"
            >
              Tiếp theo →
            </button>
          </motion.div>
        )}

        {step === 'note' && (
          <motion.div key="note" initial={{ opacity: 0, x: 28 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            <p className="text-[10px] uppercase tracking-widest text-[var(--color-serene-muted)] mb-1">
              An · Check-in
            </p>
            <h1 className="font-[var(--font-display)] text-2xl text-[var(--color-serene-ink)] mb-2 leading-snug">
              Muốn ghi thêm gì không?
            </h1>
            <p className="text-sm text-[var(--color-serene-muted)] mb-6">Không bắt buộc — chỉ dành cho bạn.</p>

            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              rows={5}
              maxLength={500}
              placeholder="Hôm nay mình…"
              className="w-full bg-white rounded-2xl p-4 text-[var(--color-serene-ink)] placeholder:text-[var(--color-serene-outline)] resize-none border border-[var(--color-serene-outline)] focus:outline-none focus:border-[var(--color-an)] text-sm"
              aria-label="Ghi chú hôm nay"
            />

            <button
              type="button"
              onClick={submit}
              disabled={loading}
              className="w-full bg-[var(--color-serene-primary)] hover:bg-[var(--color-serene-primary-dim)] text-[var(--color-serene-on-primary)] py-3.5 rounded-2xl font-semibold text-sm mt-5 transition-all disabled:opacity-50"
            >
              {loading ? 'Đang lưu…' : 'Hoàn thành ✓'}
            </button>
            <button
              type="button"
              onClick={() => setStep('sliders')}
              disabled={loading}
              className="w-full text-sm text-[var(--color-serene-muted)] mt-3 hover:text-[var(--color-serene-ink)] transition disabled:opacity-50"
            >
              ← Quay lại
            </button>
          </motion.div>
        )}

        {step === 'summary' && mood && (
          <motion.div
            key="summary"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center text-center mt-12"
          >
            <div className="text-6xl mb-4" aria-hidden="true">{mood.emoji}</div>
            <h1 className="font-[var(--font-display)] text-3xl text-[var(--color-serene-ink)] mb-3">
              Đã ghi lại!
            </h1>
            <p className="text-[var(--color-serene-muted)] mb-10 text-sm leading-relaxed max-w-xs">
              Cảm giác <strong className="text-[var(--color-serene-ink)]">{mood.label}</strong>,
              căng thẳng {stress}/10, ngủ {sleep} giờ.
              {note.trim() && ' Ghi chú đã được lưu.'}
            </p>
            <div className="flex flex-col gap-3 w-full max-w-xs">
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.chat)}
                className="bg-[var(--color-serene-primary)] text-[var(--color-serene-on-primary)] py-3.5 rounded-2xl font-semibold text-sm"
              >
                Trò chuyện với Mây
              </button>
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.home)}
                className="bg-[var(--color-serene-surface)] text-[var(--color-serene-ink)] py-3.5 rounded-2xl font-medium text-sm"
              >
                Về trang chính
              </button>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
