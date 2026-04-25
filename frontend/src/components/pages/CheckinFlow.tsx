import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { checkinService } from '../../services/checkinService'
import { ROUTE_PATHS } from '../../routes/paths'
import { toast } from 'react-toastify'
import { ChevronDown, ChevronLeft, Circle, Info } from 'lucide-react'

type Step = 'mood' | 'emotions' | 'triggers' | 'summary'

const MOOD_CATEGORIES = {
  awesome: {
    label: 'Awesome!',
    color: '#4A90E2',
    emotions: ['Joyful', 'Amazed', 'Passionate', 'Enthusiastic', 'Excited', 'Proud'],
  },
  good: {
    label: 'Good',
    color: '#4CAF50',
    emotions: ['Happy', 'Hopeful', 'Confident', 'Brave', 'Curious', 'Grateful'],
  },
  fine: {
    label: 'Fine',
    color: '#FFC107',
    emotions: ['Calm', 'Content', 'Relaxed', 'Peaceful', 'Relieved', 'Satisfied', 'Indifferent'],
  },
  bad: {
    label: 'Bad',
    color: '#FF7043',
    emotions: ['Sad', 'Angry', 'Annoyed', 'Anxious', 'Scared', 'Disgusted', 'Jealous', 'Guilty', 'Embarrassed', 'Disappointed', 'Stressed', 'Tired'],
  },
  terrible: {
    label: 'Terrible',
    color: '#E64A19',
    emotions: ['Hopeless', 'Lonely', 'Depressed'],
  },
} as const

type MoodKey = keyof typeof MOOD_CATEGORIES

const MOOD_OPTIONS: Array<{ key: MoodKey; icon: string }> = [
  { key: 'awesome', icon: '🙂' },
  { key: 'good', icon: '😊' },
  { key: 'fine', icon: '😌' },
  { key: 'bad', icon: '☹️' },
  { key: 'terrible', icon: '😣' },
]

const TRIGGER_TAGS = [
  'Health',
  'Sleep',
  'Exercise',
  'Food',
  'Hobby',
  'Money',
  'Identity',
  'Partner',
  'Friends',
  'Pet',
  'Family',
  'Colleagues',
  'Dating',
  'Work',
  'Home',
  'School',
  'Outdoors',
  'Travel',
  'Weather',
] as const

export function CheckinFlow() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('mood')
  const [selectedMood, setSelectedMood] = useState<MoodKey | null>(null)
  const [selectedEmotions, setSelectedEmotions] = useState<string[]>([])
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>([])
  const [positiveFirst, setPositiveFirst] = useState(true)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)

  const emotionToMood = useMemo(() => {
    const map = new Map<string, MoodKey>()
    for (const [moodKey, moodData] of Object.entries(MOOD_CATEGORIES) as Array<[MoodKey, (typeof MOOD_CATEGORIES)[MoodKey]]>) {
      for (const emotion of moodData.emotions) {
        map.set(emotion, moodKey)
      }
    }
    return map
  }, [])

  const orderedEmotions = useMemo(() => {
    const positive = [
      ...MOOD_CATEGORIES.awesome.emotions,
      ...MOOD_CATEGORIES.good.emotions,
      ...MOOD_CATEGORIES.fine.emotions,
    ]
    const negative = [
      ...MOOD_CATEGORIES.bad.emotions,
      ...MOOD_CATEGORIES.terrible.emotions,
    ]
    return positiveFirst ? [...positive, ...negative] : [...negative, ...positive]
  }, [positiveFirst])

  const toggleEmotion = (emotion: string) => {
    setSelectedEmotions((prev) =>
      prev.includes(emotion) ? prev.filter((item) => item !== emotion) : [...prev, emotion],
    )
  }

  const toggleTrigger = (trigger: string) => {
    setSelectedTriggers((prev) =>
      prev.includes(trigger) ? prev.filter((item) => item !== trigger) : [...prev, trigger],
    )
  }

  const submit = async () => {
    if (!selectedMood) return
    setLoading(true)
    try {
      await checkinService.quickCheckin({
        mood: selectedMood,
        emotions: selectedEmotions,
        triggers: selectedTriggers,
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
    <div className="min-h-screen bg-white/45 px-4 pb-12 pt-7 text-serene-ink backdrop-blur-xl sm:px-6">
      <AnimatePresence mode="wait">
        {step === 'mood' && (
          <motion.div key="mood" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="mx-auto w-full max-w-[460px]">
            <header className="mb-5 flex items-center justify-between">
              <button type="button" onClick={() => navigate(ROUTE_PATHS.home)} className="rounded-full p-2 text-serene-muted transition hover:bg-white/60" aria-label="Quay lại trang chủ">
                <ChevronLeft className="h-6 w-6" />
              </button>
              <h1 className="text-[2rem] font-semibold leading-none">Mood check-in</h1>
              <Info className="h-5 w-5 text-serene-muted" />
            </header>

            <section className="rounded-[30px] border border-white/45 bg-white/65 p-6 shadow-[0_20px_60px_rgba(72,87,121,0.14)] backdrop-blur-xl">
              <h2 className="mb-5 text-4xl font-semibold leading-tight">How are you feeling?</h2>
              {MOOD_OPTIONS.map(({ key, icon }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSelectedMood(key)}
                  className="flex w-full items-center gap-4 border-b border-serene-ink/10 py-4 text-left transition hover:bg-white/55"
                >
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-serene-muted/35">
                    {selectedMood === key ? <Circle className="h-4 w-4 fill-serene-primary text-serene-primary" /> : <Circle className="h-4 w-4 text-transparent" />}
                  </span>
                  <span className="text-3xl">{icon}</span>
                  <span className="text-2xl text-serene-ink">{MOOD_CATEGORIES[key].label}</span>
                </button>
              ))}
            </section>

            <p className="mt-5 text-lg text-serene-muted">A mood is an overall state of mind that's long lasting.</p>
            <button
              type="button"
              onClick={() => setStep('emotions')}
              disabled={!selectedMood}
              className="mt-8 w-full rounded-full bg-serene-primary py-4 text-2xl font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </motion.div>
        )}

        {step === 'emotions' && selectedMood && (
          <motion.div key="emotions" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="mx-auto w-full max-w-[460px]">
            <header className="mb-5 flex items-center justify-between">
              <button type="button" onClick={() => setStep('mood')} className="rounded-full p-2 text-serene-muted transition hover:bg-white/60" aria-label="Quay lại">
                <ChevronLeft className="h-6 w-6" />
              </button>
              <h1 className="text-[2rem] font-semibold leading-none">Mood check-in</h1>
              <Info className="h-5 w-5 text-serene-muted" />
            </header>

            <section className="rounded-[30px] border border-white/45 bg-white/65 p-6 shadow-[0_20px_60px_rgba(72,87,121,0.14)] backdrop-blur-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-4xl font-semibold leading-tight">Which emotions best describe how you feel?</h2>
                <button
                  type="button"
                  onClick={() => setPositiveFirst((value) => !value)}
                  className="rounded-full p-2 text-serene-muted transition hover:bg-white/60"
                  aria-label="Đổi thứ tự cảm xúc"
                >
                  <ChevronDown className={`h-5 w-5 transition-transform ${positiveFirst ? '' : 'rotate-180'}`} />
                </button>
              </div>
              <div className="flex flex-wrap gap-2.5">
                {orderedEmotions.map((emotion) => {
                  const isSelected = selectedEmotions.includes(emotion)
                  const emotionMood = emotionToMood.get(emotion) || selectedMood
                  const selectedColor = MOOD_CATEGORIES[emotionMood].color
                  return (
                    <button
                      key={emotion}
                      type="button"
                      onClick={() => toggleEmotion(emotion)}
                      className="rounded-full px-4 py-2 text-xl transition-all"
                      style={
                        isSelected
                          ? { backgroundColor: selectedColor, color: '#fff' }
                          : { backgroundColor: 'rgba(255,255,255,0.72)', color: 'var(--color-serene-ink)' }
                      }
                    >
                      {emotion}
                    </button>
                  )
                })}
              </div>
            </section>

            <p className="mt-5 text-lg text-serene-muted">
              An emotion is a short-lived reaction, such as joy, anger, or sadness, to an event or meaningful experience.
            </p>
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setStep('mood')}
                className="w-1/3 rounded-full border border-white/50 bg-white/30 py-3 text-lg font-medium text-serene-muted transition hover:bg-white/60"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep('triggers')}
                className="w-2/3 rounded-full bg-serene-primary py-3 text-xl font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105"
              >
                Next
              </button>
            </div>
          </motion.div>
        )}

        {step === 'triggers' && selectedMood && (
          <motion.div key="triggers" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="mx-auto w-full max-w-[460px]">
            <header className="mb-5 flex items-center justify-between">
              <button type="button" onClick={() => setStep('emotions')} className="rounded-full p-2 text-serene-muted transition hover:bg-white/60" aria-label="Quay lại">
                <ChevronLeft className="h-6 w-6" />
              </button>
              <h1 className="text-[2rem] font-semibold leading-none">Mood check-in</h1>
              <Info className="h-5 w-5 text-serene-muted" />
            </header>

            <section className="rounded-[30px] border border-white/45 bg-white/65 p-6 shadow-[0_20px_60px_rgba(72,87,121,0.14)] backdrop-blur-xl">
              <h2 className="mb-5 text-4xl font-semibold leading-tight">What's making you feel this way?</h2>
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
                          : { backgroundColor: 'rgba(255,255,255,0.72)', color: 'var(--color-serene-ink)' }
                      }
                    >
                      {trigger}
                    </button>
                  )
                })}
              </div>

              <h3 className="mt-8 text-4xl font-semibold leading-tight">Anything else to add?</h3>
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={4}
                maxLength={500}
                placeholder="Add a note to help you remember this feeling or moment"
                className="mt-3 w-full resize-none rounded-3xl border border-white/50 bg-white/75 px-4 py-4 text-xl text-serene-ink placeholder:text-serene-muted/60 focus:border-serene-primary/30 focus:outline-none"
              />
            </section>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setStep('emotions')}
                disabled={loading}
                className="w-1/3 rounded-full border border-white/50 bg-white/30 py-3 text-lg font-medium text-serene-muted transition hover:bg-white/60 disabled:opacity-50"
              >
                Back
              </button>
              <button
                type="button"
                onClick={submit}
                disabled={loading}
                className="w-2/3 rounded-full bg-serene-primary py-3 text-xl font-semibold text-serene-on-primary shadow-lg shadow-serene-primary/20 transition hover:brightness-105 disabled:opacity-60"
              >
                {loading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </motion.div>
        )}

        {step === 'summary' && selectedMood && (
          <motion.div
            key="summary"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mx-auto mt-8 flex w-full max-w-[460px] flex-col rounded-[30px] border border-white/45 bg-white/65 p-6 text-serene-ink shadow-[0_20px_60px_rgba(72,87,121,0.14)] backdrop-blur-xl"
          >
            <p className="text-lg uppercase tracking-[0.22em] text-serene-primary/65">Saved</p>
            <h2 className="mt-1 text-5xl font-semibold">Check-in complete</h2>
            <p className="mt-4 text-xl text-serene-muted">
              Mood: <span className="font-semibold">{MOOD_CATEGORIES[selectedMood].label}</span>
            </p>

            <div className="mt-6">
              <p className="text-sm uppercase tracking-[0.22em] text-serene-primary/60">7-day streak</p>
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

            {selectedEmotions.length > 0 && (
              <div className="mt-6">
                <p className="mb-2 text-sm uppercase tracking-[0.22em] text-serene-primary/60">Emotions</p>
                <div className="flex flex-wrap gap-2">
                  {selectedEmotions.map((emotion) => (
                    <span
                      key={emotion}
                      className="rounded-full px-3 py-1.5 text-sm text-white"
                      style={{ backgroundColor: MOOD_CATEGORIES[emotionToMood.get(emotion) || selectedMood].color }}
                    >
                      {emotion}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedTriggers.length > 0 && (
              <p className="mt-5 text-sm text-serene-muted">Triggers: {selectedTriggers.join(', ')}</p>
            )}

            {note.trim() && <p className="mt-3 rounded-2xl bg-white/70 p-3 text-sm text-serene-ink">{note.trim()}</p>}

            <div className="mt-7 flex flex-col gap-3">
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.chat)}
                className="rounded-full bg-serene-primary py-3 text-xl font-semibold text-serene-on-primary"
              >
                Chat with Mây
              </button>
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.home)}
                className="rounded-full border border-white/50 bg-white/30 py-3 text-lg font-medium text-serene-muted"
              >
                Go Home
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
