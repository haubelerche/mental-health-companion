import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { checkinService, type CheckinRewardResult, type CheckinStreakResult } from '../../services/checkinService'
import { ROUTE_PATHS } from '../../routes/paths'
import { toast } from 'react-toastify'
import { ChevronLeft, Info } from 'lucide-react'
import { StreakCelebration } from './StreakCelebration'
import { MoodWordChips } from './MoodWordChips'

export type CheckinLocationState = {
  moodWords?: string[]
}

type Step = 'mood' | 'triggers' | 'summary'

const MOOD_CATEGORIES = {
  awesome: {
    label: 'Rất tốt',
    color: '#4A90E2',
  },
  good: {
    label: 'Tốt',
    color: '#4CAF50',
  },
  fine: {
    label: 'Bình thường',
    color: '#FFC107',
  },
  bad: {
    label: 'Không tốt',
    color: '#FF7043',
  },
  terrible: {
    label: 'Tệ lắm',
    color: '#E64A19',
  },
} as const

type MoodKey = keyof typeof MOOD_CATEGORIES

/** Map từ chip "Tâm trạng hôm nay" (tiếng Việt) → nhóm gửi API; đồng bộ với MoodWordChips mặc định. */
const VI_MOOD_WORD_TO_KEY: Record<string, MoodKey> = {
  'Bình yên': 'fine',
  'Hứng khởi': 'awesome',
  'Biết ơn': 'good',
  'Tự tin': 'good',
  'Mệt mỏi': 'bad',
  'Lo âu': 'bad',
  'Buồn': 'bad',
  'Căng thẳng': 'bad',
  'Vui vẻ': 'good',
  'Trống rỗng': 'fine',
  'Cô đơn': 'bad',
  'Bối rối': 'fine',
}

const SEVERITY_RANK: MoodKey[] = ['terrible', 'bad', 'fine', 'good', 'awesome']

function deriveMoodFromWords(words: string[]): MoodKey {
  if (words.length === 0) return 'fine'
  const keys = words.map((w) => VI_MOOD_WORD_TO_KEY[w] ?? 'fine')
  return keys.reduce((worst, m) =>
    SEVERITY_RANK.indexOf(m) < SEVERITY_RANK.indexOf(worst) ? m : worst,
  keys[0])
}

const TRIGGER_TAGS = [
  'Sức khoẻ',
  'Giấc ngủ',
  'Vận động',
  'Ăn uống',
  'Sở thích',
  'Tài chính',
  'Bản thân',
  'Người yêu',
  'Bạn bè',
  'Thú cưng',
  'Gia đình',
  'Đồng nghiệp',
  'Hẹn hò',
  'Công việc',
  'Nhà cửa',
  'Học tập',
  'Thiên nhiên',
  'Du lịch',
  'Thời tiết',
] as const

export function CheckinFlow() {
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState<Step>('mood')
  const [selectedMood, setSelectedMood] = useState<MoodKey | null>(null)
  const [moodWords, setMoodWords] = useState<string[]>([])
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [showStreak, setShowStreak] = useState(false)
  const [checkinReward, setCheckinReward] = useState<CheckinRewardResult | null>(null)
  const [checkinStreak, setCheckinStreak] = useState<CheckinStreakResult | null>(null)

  useEffect(() => {
    const st = location.state as CheckinLocationState | null
    const words = (st?.moodWords ?? []).filter(Boolean)
    if (words.length === 0) return
    setMoodWords(words)
    setSelectedMood(deriveMoodFromWords(words))
    setStep('triggers')
  }, [location.state])

  const goToTriggersFromMood = () => {
    if (moodWords.length === 0) return
    const derived = deriveMoodFromWords(moodWords)
    setSelectedMood(derived)
    setStep('triggers')
  }

  const toggleTrigger = (trigger: string) => {
    setSelectedTriggers((prev) =>
      prev.includes(trigger) ? prev.filter((item) => item !== trigger) : [...prev, trigger],
    )
  }

  const submit = async () => {
    const mood = selectedMood ?? deriveMoodFromWords(moodWords)
    if (moodWords.length === 0) return
    setLoading(true)
    try {
      const result = await checkinService.quickCheckin({
        mood,
        emotions: moodWords,
        triggers: selectedTriggers,
        note: note.trim() || null,
      })
      setCheckinReward(result?.reward ?? null)
      setCheckinStreak(result?.streak ?? null)
      setSelectedMood(mood)
      setStep('summary')
      setTimeout(() => setShowStreak(true), 600)
    } catch {
      toast.error('Không thể lưu check-in cảm xúc. Thử lại nhé.')
    } finally {
      setLoading(false)
    }
  }

  const moodKeyForWord = (word: string): MoodKey =>
    VI_MOOD_WORD_TO_KEY[word] ?? selectedMood ?? 'fine'

  return (
    <div className="min-h-screen bg-theme-surface/65 px-4 pb-12 pt-7 backdrop-blur-xl sm:px-6">
      <StreakCelebration
        open={showStreak}
        streakDays={checkinStreak?.current ?? 0}
        heartsEarned={checkinReward?.amount ?? 0}
        onClose={() => setShowStreak(false)}
        onClaim={() => {
          setShowStreak(false)
          navigate(ROUTE_PATHS.home)
        }}
      />
      <AnimatePresence mode="wait">
        {step === 'mood' && (
          <motion.div key="mood" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="mx-auto w-full max-w-[460px]">
            <header className="mb-5 flex items-center justify-between">
              <button type="button" onClick={() => navigate(ROUTE_PATHS.home)} className="rounded-full p-2 text-theme-text-primary transition hover:bg-white/60" aria-label="Quay lại trang chủ">
                <ChevronLeft className="h-6 w-6" />
              </button>
              <h1 className="text-[2rem] font-semibold leading-none ">Check-in cảm xúc</h1>
              <Info className="h-5 w-5" />
            </header>

            <section className="rounded-[30px] border border-theme-border bg-theme-surface/80 p-6 shadow-md backdrop-blur-xl">
              <h2 className="mb-5 text-4xl font-semibold leading-tight">Tâm trạng hôm nay?</h2>
              <MoodWordChips selected={moodWords} onChange={setMoodWords} />
            </section>

            <p className="mt-5 text-lg text-theme-text-secondary">Chọn một hoặc nhiều từ mô tả đúng nhất cảm giác của bạn lúc này.</p>
            <button
              type="button"
              onClick={goToTriggersFromMood}
              disabled={moodWords.length === 0}
              className="mt-8 w-full rounded-full bg-theme-accent py-4 text-2xl font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Tiếp theo
            </button>
          </motion.div>
        )}

        {step === 'triggers' && selectedMood != null && moodWords.length > 0 && (
          <motion.div key="triggers" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="mx-auto w-full max-w-[460px]">
            <header className="mb-5 flex items-center justify-between">
              <button type="button" onClick={() => setStep('mood')} className="rounded-full p-2 text-serene-muted transition hover:bg-white/60" aria-label="Quay lại">
                <ChevronLeft className="h-6 w-6" />
              </button>
              <h1 className="text-[2rem] font-semibold leading-none">Check-in cảm xúc</h1>
              <Info className="h-5 w-5 text-serene-muted" />
            </header>

            <section className="rounded-[30px] border border-theme-border  bg-theme-surface/80 p-6 shadow-md backdrop-blur-xl">
              <h2 className="mb-5 text-4xl font-semibold leading-tight">Điều gì ảnh hưởng đến bạn hôm nay?</h2>
              <div className="flex flex-wrap gap-2.5">
                {TRIGGER_TAGS.map((trigger) => {
                  const isSelected = selectedTriggers.includes(trigger)
                  return (
                    <button
                      key={trigger}
                      type="button"
                      onClick={() => toggleTrigger(trigger)}
                      className="rounded-full px-4 py-2 text-xl transition-all"
                      style={
                        isSelected
                          ? { backgroundColor: MOOD_CATEGORIES[selectedMood].color, color: '#fff' }
                          : { backgroundColor: 'var(--color-theme-surface)', color: 'var(--color-theme-text-secondary)', border: '1px solid var(--color-theme-border) ' }
                      }
                    >
                      {trigger}
                    </button>
                  )
                })}
              </div>

              <h3 className="mt-8 text-4xl font-semibold leading-tight">Ghi chú thêm?</h3>
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={4}
                maxLength={500}
                placeholder="Ghi lại điều gì đó về khoảnh khắc này..."
                className="mt-3 w-full resize-none rounded-3xl border border-theme-border bg- theme-surface px-4 py-4 text-xl text-theme-text-secondary placeholder:text-serene-muted/60 focus:border-serene-primary/30 focus:outline-none"
              />
            </section>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setStep('mood')}
                disabled={loading}
                className="w-1/3 rounded-full border border-theme-border bg-theme-surface py-3 text-lg font-medium text-theme-text-secondary transition hover:bg-theme-surface/80 disabled:opacity-50"
              >
                Quay lại
              </button>
              <button
                type="button"
                onClick={submit}
                disabled={loading}
                className="w-2/3 rounded-full bg-theme-accent py-3 text-xl font-semibold text-white cursor-pointer transition hover:brightness-105 disabled:opacity-60"
              >
                {loading ? 'Đang lưu...' : 'Lưu lại'}
              </button>
            </div>
          </motion.div>
        )}

        {step === 'summary' && selectedMood != null && (
          <motion.div
            key="summary"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mx-auto mt-8 flex w-full max-w-[460px] flex-col rounded-[30px] border border-white/45 bg-white/65 p-6 text-serene-ink shadow-[0_20px_60px_rgba(72,87,121,0.14)] backdrop-blur-xl"
          >
            <div className="flex items-center justify-between">
              <p className="text-lg uppercase tracking-[0.22em] text-serene-primary/65">Đã lưu</p>
              {checkinReward?.granted && checkinReward.amount > 0 && (
                <span className="rounded-full bg-rose-50 px-3 py-1 text-sm font-semibold text-rose-500">
                  +{checkinReward.amount} tim
                </span>
              )}
            </div>
            <h2 className="mt-1 text-5xl font-semibold">Xong rồi</h2>
            <p className="mt-4 text-xl text-serene-muted">
              Tổng quan: <span className="font-semibold text-serene-ink">{MOOD_CATEGORIES[selectedMood].label}</span>
            </p>

            <div className="mt-6">
              <p className="text-sm uppercase tracking-[0.22em] text-serene-primary/60">Chuỗi 7 ngày</p>
              <div className="mt-3 flex gap-2">
                {[...Array.from({ length: 7 }).keys()].map((idx) => (
                  <span
                    key={idx}
                    className="h-3 w-8 rounded-full"
                    style={{ backgroundColor: idx < 4 ? MOOD_CATEGORIES[selectedMood].color : 'rgba(255,255,255,0.7)' }}
                  />
                ))}
              </div>
            </div>

            {moodWords.length > 0 && (
              <div className="mt-6">
                <p className="mb-2 text-sm uppercase tracking-[0.22em] text-serene-primary/60">Tâm trạng bạn chọn</p>
                <div className="flex flex-wrap gap-2">
                  {moodWords.map((word) => (
                    <span
                      key={word}
                      className="rounded-full px-3 py-1.5 text-sm text-white"
                      style={{ backgroundColor: MOOD_CATEGORIES[moodKeyForWord(word)].color }}
                    >
                      {word}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedTriggers.length > 0 && (
              <p className="mt-5 text-sm text-serene-muted">Yếu tố: {selectedTriggers.join(', ')}</p>
            )}

            {note.trim() && <p className="mt-3 rounded-2xl bg-white/70 p-3 text-sm text-serene-ink">{note.trim()}</p>}

            <div className="mt-7 flex flex-col gap-3">
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.chat)}
                className="rounded-full bg-serene-primary py-3 text-xl font-semibold text-serene-on-primary"
              >
                Chat với Mây
              </button>
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.home)}
                className="rounded-full border border-white/50 bg-white/30 py-3 text-lg font-medium text-serene-muted"
              >
                Về trang chủ
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
