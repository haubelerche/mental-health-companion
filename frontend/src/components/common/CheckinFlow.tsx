import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Check, ChevronLeft, HeartPulse, Info, Sparkles } from 'lucide-react'
import { toast } from 'react-toastify'
import { checkinService, type CheckinRewardResult, type CheckinStreakResult } from '../../services/checkinService'
import { ROUTE_PATHS } from '../../routes/paths'
import { StreakCelebration } from './StreakCelebration'
import { MoodWordChips } from './MoodWordChips'
import bgCheckinDay from '../../assets/backgrounds/bg-checkin-day.gif'
import bgCheckinNight from '../../assets/backgrounds/bg-checkin-night.gif'

export type CheckinLocationState = {
  moodWords?: string[]
}

type Step = 'mood' | 'triggers' | 'summary'

const MOOD_CATEGORIES = {
  awesome: { label: 'Rất tốt', color: '#4A90E2' },
  good: { label: 'Tốt', color: '#4CAF50' },
  fine: { label: 'Bình thường', color: '#D6A531' },
  bad: { label: 'Không tốt', color: '#FF7043' },
  terrible: { label: 'Tệ lắm', color: '#E64A19' },
} as const

type MoodKey = keyof typeof MOOD_CATEGORIES

const MOOD_WORDS = [
  'Bình yên',
  'Hứng khởi',
  'Biết ơn',
  'Tự tin',
  'Mệt mỏi',
  'Lo âu',
  'Buồn rầu',
  'Căng thẳng',
  'Vui vẻ',
  'Trống rỗng',
  'Cô đơn',
  'Bối rối',
]

const VI_MOOD_WORD_TO_KEY: Record<string, MoodKey> = {
  'Bình yên': 'fine',
  'Hứng khởi': 'awesome',
  'Biết ơn': 'good',
  'Tự tin': 'good',
  'Mệt mỏi': 'bad',
  'Lo âu': 'bad',
  'Buồn': 'bad',
  'Buồn rầu': 'bad',
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
  return keys.reduce(
    (worst, m) => (SEVERITY_RANK.indexOf(m) < SEVERITY_RANK.indexOf(worst) ? m : worst),
    keys[0],
  )
}

const TRIGGER_TAGS = [
  'Sức khỏe',
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

function isDaytimeCheckin() {
  const hour = new Date().getHours()
  return hour >= 6 && hour < 18
}

function stepIndex(step: Step) {
  return step === 'mood' ? 0 : step === 'triggers' ? 1 : 2
}

export function CheckinFlow() {
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState<Step>('mood')
  const [selectedMood, setSelectedMood] = useState<MoodKey | null>(null)
  const [moodWords, setMoodWords] = useState<string[]>([])
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [isDaytime, setIsDaytime] = useState(() => isDaytimeCheckin())
  const [showStreak, setShowStreak] = useState(false)
  const [checkinReward, setCheckinReward] = useState<CheckinRewardResult | null>(null)
  const [checkinStreak, setCheckinStreak] = useState<CheckinStreakResult | null>(null)

  useEffect(() => {
    const timer = window.setInterval(() => setIsDaytime(isDaytimeCheckin()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const st = location.state as CheckinLocationState | null
    const words = (st?.moodWords ?? []).filter(Boolean)
    if (words.length === 0) return
    setMoodWords(words)
    setSelectedMood(deriveMoodFromWords(words))
    setStep('triggers')
  }, [location.state])

  const background = isDaytime ? bgCheckinDay : bgCheckinNight
  const mood = selectedMood ?? deriveMoodFromWords(moodWords)
  const currentStep = stepIndex(step)
  const canGoNext = moodWords.length > 0

  const selectedMoodLabel = useMemo(() => MOOD_CATEGORIES[mood].label, [mood])

  const goToTriggersFromMood = () => {
    if (!canGoNext) return
    setSelectedMood(deriveMoodFromWords(moodWords))
    setStep('triggers')
  }

  const toggleTrigger = (trigger: string) => {
    setSelectedTriggers((prev) =>
      prev.includes(trigger) ? prev.filter((item) => item !== trigger) : [...prev, trigger],
    )
  }

  const submit = async () => {
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

  const moodKeyForWord = (word: string): MoodKey => VI_MOOD_WORD_TO_KEY[word] ?? selectedMood ?? 'fine'

  return (
    <div className="relative min-h-screen overflow-hidden text-[#2f332b]">
      <div className="fixed inset-0 z-0">
        <img src={background} alt="" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-[#17251e]/35" />
      </div>

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-6">
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

        <section className="grid h-[min(660px,calc(100dvh-48px))] w-full max-w-[430px] grid-rows-[auto_auto_1fr_auto] overflow-hidden rounded-[28px] border border-[#f6eedf]/70 bg-[#efe5d2]/92 p-5 shadow-[0_28px_80px_rgba(16,28,22,0.34)] backdrop-blur-md sm:max-w-[460px] sm:p-6">
          <header className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => (step === 'mood' ? navigate(ROUTE_PATHS.home) : setStep(step === 'summary' ? 'triggers' : 'mood'))}
              className="grid h-10 w-10 place-items-center rounded-full border border-[#d8cbb5] bg-[#fbf5ea]/80 text-[#4c5f50] transition hover:bg-white"
              aria-label="Quay lại"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <span className="inline-flex items-center gap-2 rounded-full bg-[#fbf5ea]/90 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5b6f5f]">
              <Sparkles className="h-3.5 w-3.5" />
              SereneAI
            </span>
            <Info className="h-5 w-5 text-[#6d756a]" />
          </header>

          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#6d756a]">
              Check-in cảm xúc
            </p>
            <h1 className="mt-2 font-display text-[2.35rem] leading-[1.05] text-[#2f332b] sm:text-[2.7rem]">
              Một góc nhỏ để bạn được lắng nghe.
            </h1>
            <div className="mt-5 grid grid-cols-3 gap-2">
              {['Cảm xúc', 'Yếu tố', 'Tổng kết'].map((label, idx) => (
                <div
                  key={label}
                  className={[
                    'h-2 rounded-full transition',
                    idx <= currentStep ? 'bg-[#526f5f]' : 'bg-[#d8cbb5]',
                  ].join(' ')}
                  aria-label={label}
                />
              ))}
            </div>
          </div>

          <div className="min-h-0 overflow-hidden pt-5">
            <AnimatePresence mode="wait">
              {step === 'mood' && (
                <motion.div
                  key="mood"
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -18 }}
                  className="flex h-full flex-col"
                >
                  <div className="rounded-[22px] border border-[#dfd2ba] bg-[#fbf5ea]/82 p-4 shadow-sm">
                    <h2 className="text-xl font-semibold text-[#33372f]">Tâm trạng hôm nay?</h2>
                    <p className="mt-2 text-sm leading-relaxed text-[#62695f]">
                      Chọn một hoặc nhiều từ gần nhất với cảm giác của bạn lúc này.
                    </p>
                    <MoodWordChips words={MOOD_WORDS} selected={moodWords} onChange={setMoodWords} className="mt-4" />
                  </div>
                </motion.div>
              )}

              {step === 'triggers' && (
                <motion.div
                  key="triggers"
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -18 }}
                  className="flex h-full min-h-0 flex-col"
                >
                  <div className="min-h-0 flex-1 overflow-y-auto rounded-[22px] border border-[#dfd2ba] bg-[#fbf5ea]/82 p-4 shadow-sm">
                    <h2 className="text-xl font-semibold text-[#33372f]">Điều gì ảnh hưởng đến bạn hôm nay?</h2>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {TRIGGER_TAGS.map((trigger) => {
                        const isSelected = selectedTriggers.includes(trigger)
                        return (
                          <button
                            key={trigger}
                            type="button"
                            onClick={() => toggleTrigger(trigger)}
                            className="rounded-full border px-3.5 py-2 text-sm font-medium transition"
                            style={
                              isSelected
                                ? { backgroundColor: MOOD_CATEGORIES[mood].color, borderColor: MOOD_CATEGORIES[mood].color, color: '#fff' }
                                : { backgroundColor: '#fffaf0', borderColor: '#ded0b8', color: '#4e564a' }
                            }
                          >
                            {trigger}
                          </button>
                        )
                      })}
                    </div>

                    <label className="mt-5 block text-sm font-semibold text-[#33372f]" htmlFor="checkin-note">
                      Ghi chú thêm
                    </label>
                    <textarea
                      id="checkin-note"
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      rows={4}
                      maxLength={500}
                      placeholder="Ghi lại điều gì đó về khoảnh khắc này..."
                      className="mt-2 w-full resize-none rounded-[18px] border border-[#ded0b8] bg-[#fffaf0] px-4 py-3 text-sm leading-relaxed text-[#33372f] placeholder:text-[#8a8b80] focus:border-[#526f5f] focus:outline-none"
                    />
                  </div>
                </motion.div>
              )}

              {step === 'summary' && (
                <motion.div
                  key="summary"
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -18 }}
                  className="flex h-full flex-col"
                >
                  <div className="rounded-[22px] border border-[#dfd2ba] bg-[#fbf5ea]/82 p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#6d756a]">Đã lưu</p>
                        <h2 className="mt-1 text-3xl font-semibold text-[#33372f]">Xong rồi</h2>
                      </div>
                      <span className="grid h-12 w-12 place-items-center rounded-full bg-[#526f5f] text-white">
                        <Check className="h-6 w-6" />
                      </span>
                    </div>

                    <p className="mt-5 text-sm text-[#62695f]">
                      Tổng quan: <span className="font-semibold text-[#33372f]">{selectedMoodLabel}</span>
                    </p>
                    {checkinReward?.granted && checkinReward.amount > 0 && (
                      <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-500">
                        <HeartPulse className="h-4 w-4" />
                        +{checkinReward.amount} tim
                      </p>
                    )}

                    <div className="mt-5 flex flex-wrap gap-2">
                      {moodWords.map((word) => (
                        <span
                          key={word}
                          className="rounded-full px-3 py-1.5 text-xs font-medium text-white"
                          style={{ backgroundColor: MOOD_CATEGORIES[moodKeyForWord(word)].color }}
                        >
                          {word}
                        </span>
                      ))}
                    </div>

                    {selectedTriggers.length > 0 && (
                      <p className="mt-5 text-sm leading-relaxed text-[#62695f]">
                        Yếu tố: <span className="text-[#33372f]">{selectedTriggers.join(', ')}</span>
                      </p>
                    )}
                    {note.trim() && (
                      <p className="mt-4 rounded-[18px] bg-[#fffaf0] p-3 text-sm leading-relaxed text-[#33372f]">
                        {note.trim()}
                      </p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <footer className="mt-5 grid grid-cols-[1fr_auto] gap-3">
            {step === 'summary' ? (
              <>
                <button
                  type="button"
                  onClick={() => navigate(ROUTE_PATHS.chat)}
                  className="rounded-full bg-[#526f5f] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:brightness-105"
                >
                  Chat với Serene
                </button>
                <button
                  type="button"
                  onClick={() => navigate(ROUTE_PATHS.home)}
                  className="rounded-full border border-[#d8cbb5] bg-[#fbf5ea]/80 px-5 py-3 text-sm font-semibold text-[#4c5f50] transition hover:bg-white"
                >
                  Trang chủ
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={step === 'mood' ? goToTriggersFromMood : submit}
                  disabled={(step === 'mood' && !canGoNext) || loading}
                  className="inline-flex min-w-[118px] justify-self-end items-center justify-center gap-2 rounded-full bg-[#526f5f] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? 'Đang lưu' : 'Next'}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
              </>
            )}
          </footer>
        </section>
      </div>
    </div>
  )
}
