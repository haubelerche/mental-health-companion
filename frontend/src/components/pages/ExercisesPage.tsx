import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Pause, Play, Settings, Waves, X } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ocean from '../../assets/bg-reflect.png'
import { ROUTE_PATHS } from '../../routes/paths'
import { exerciseService, FALLBACK_EXERCISES, findFallbackExercise, type ExerciseItem } from '../../services/exerciseService'
import {
    APP_SETTINGS_STORAGE_KEY,
    APP_SETTINGS_UPDATED_EVENT,
    readAppSettings,
    type AppSettings,
} from '../../utils/appSettings'

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function getBreathPhase(exercise: ExerciseItem, elapsed: number) {
  if (!exercise.pattern) {
    const stepDuration = Math.max(1, Math.floor(exercise.duration_sec / exercise.steps.length))
    const stepIndex = Math.min(exercise.steps.length - 1, Math.floor(elapsed / stepDuration))
    return {
      label: exercise.steps[stepIndex],
      count: Math.max(1, stepDuration - (elapsed % stepDuration)),
      scale: 1.04,
      stepIndex,
    }
  }

  const sequence = [
    { label: 'Hít vào', duration: exercise.pattern.inhale, scale: 1.2 },
    { label: 'Giữ', duration: exercise.pattern.hold, scale: 1.32 },
    { label: 'Thở ra', duration: exercise.pattern.exhale, scale: 0.92 },
  ]
  if (exercise.pattern.hold2 && exercise.pattern.hold2 > 0) {
    sequence.push({ label: 'Giữ', duration: exercise.pattern.hold2, scale: 1.08 })
  }
  const cycleDuration = sequence.reduce((sum, phase) => sum + phase.duration, 0)
  let cursor = elapsed % cycleDuration
  for (const phase of sequence) {
    if (cursor < phase.duration) {
      return {
        label: phase.label,
        count: phase.duration - cursor,
        scale: phase.scale,
        stepIndex: sequence.findIndex((item) => item.label === phase.label),
      }
    }
    cursor -= phase.duration
  }
  return { label: 'Hít vào', count: exercise.pattern.inhale, scale: 1.1, stepIndex: 0 }
}

export function ExercisesPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [isDark, setIsDark] = useState(() => readAppSettings().mode === 'dark')

  useEffect(() => {
      const syncThemeMode = (settings: AppSettings) => {
          setIsDark(settings.mode === 'dark')
      }

      const handleSettingsUpdated = (event: Event) => {
          const customEvent = event as CustomEvent<AppSettings>
          if (customEvent.detail) {
              syncThemeMode(customEvent.detail)
          }
      }

      const handleStorageUpdated = (event: StorageEvent) => {
          if (event.key !== APP_SETTINGS_STORAGE_KEY) {
              return
          }
          syncThemeMode(readAppSettings())
      }

      window.addEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
      window.addEventListener('storage', handleStorageUpdated)
      return () => {
          window.removeEventListener(APP_SETTINGS_UPDATED_EVENT, handleSettingsUpdated as EventListener)
          window.removeEventListener('storage', handleStorageUpdated)
      }
  }, [])

  const [exercises, setExercises] = useState<ExerciseItem[]>(FALLBACK_EXERCISES)
  const [selectedId, setSelectedId] = useState(FALLBACK_EXERCISES[0].id)
  const [elapsed, setElapsed] = useState(0)
  const [isRunning, setIsRunning] = useState(false)

  useEffect(() => {
    exerciseService
      .list()
      .then((data) => {
        if (data.items.length) setExercises(data.items)
      })
      .catch(() => undefined)
  }, [])

  const selectedFromQuery = searchParams.get('exercise')
  const isHubMode = !selectedFromQuery
  const activeId = searchParams.get('exercise') || selectedId
  const exercise = exercises.find((item) => item.id === activeId) ?? findFallbackExercise(activeId)
  const remaining = Math.max(0, exercise.duration_sec - elapsed)
  const progress = Math.min(100, Math.round((elapsed / exercise.duration_sec) * 100))
  const phase = useMemo(() => getBreathPhase(exercise, elapsed), [exercise, elapsed])
  const isDone = elapsed >= exercise.duration_sec
  const hubCards = ['box_breath', 'breath_478', 'equal_breath', 'custom_breath']
    .map((id) => exercises.find((item) => item.id === id) ?? findFallbackExercise(id))

  const getPatternLabel = (item: ExerciseItem) => {
    if (!item.pattern) return 'Đặt mẫu của bạn'
    const parts = [item.pattern.inhale, item.pattern.hold, item.pattern.exhale]
    if (item.pattern.hold2 && item.pattern.hold2 > 0) parts.push(item.pattern.hold2)
    return parts.join('-')
  }

  const getPurpose = (id: string) => {
    if (id === 'box_breath') return 'Thư giãn'
    if (id === 'breath_478') return 'Ngủ'
    if (id === 'equal_breath') return 'Tập trung'
    if (id === 'custom_breath') return 'Tự do'
    return 'Breathing'
  }

  useEffect(() => {
    if (!isRunning || isDone) return undefined
    const timer = window.setInterval(() => {
      setElapsed((value) => {
        const next = Math.min(exercise.duration_sec, value + 1)
        if (next >= exercise.duration_sec) setIsRunning(false)
        return next
      })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [exercise.duration_sec, isDone, isRunning])

  const startExercise = (id: string) => {
    setSearchParams({ exercise: id })
    setSelectedId(id)
    setElapsed(0)
    setIsRunning(false)
  }

  const backToHub = () => {
    setSearchParams({})
    setElapsed(0)
    setIsRunning(false)
  }

  const resetExercise = () => {
    setElapsed(0)
    setIsRunning(false)
  }

  return (
    <div className={`rounded-xl ${isDark ? 'text-white' : 'text-serene-ink'} sm:-m-8 lg:-m-12`}>
      <div className="fixed inset-0">
        <img src={ocean} alt="Background" className="h-full w-full object-cover" />
        <div className='absolute inset-0 bg-linear-to-t from-black/10 to-black/20' />
      </div>
      <div className="relative mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-8">
        {isHubMode ? (
          <section className={`rounded-4xl border ${isDark ? 'border-white/10 bg-black/40' : 'border-white/40 bg-serene-bg/75'} p-5 shadow-md backdrop-blur-xl md:p-8`}>
            <header className="mb-8 flex items-center justify-between">
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.resources)}
                className={`flex h-11 w-11 items-center justify-center rounded-full border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/50 bg-white/70'} ${isDark ? 'text-white' : 'text-serene-ink'} backdrop-blur-md transition duration-200 ease-in-out hover:bg-white/10`}
                aria-label="Quay lại thư viện"
              >
                <X className="h-5 w-5" />
              </button>
              <h1 className={`font-display text-3xl ${isDark ? 'text-white' : 'text-serene-ink'} md:text-4xl`}>Các bài tập hít thở</h1>
              <span className="h-11 w-11" />
            </header>

            <h2 className={`mb-7 font-display text-4xl leading-tight ${isDark ? 'text-white' : 'text-serene-ink'} md:text-2xl`}>
              Chọn một bài tập để thực hành
            </h2>

            <section className="grid gap-4 sm:grid-cols-2">
              {hubCards.map((item) => (
                <motion.button
                  key={item.id}
                  type="button"
                  onClick={() => startExercise(item.id)}
                  whileHover={{ y: -4, scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  transition={{ duration: 0.22, ease: 'easeInOut' }}
                  className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/5 hover:bg-white/10' : 'border-white/45 bg-white/72 hover:bg-white/86'} p-5 text-left shadow-[0_10px_24px_rgba(72,78,90,0.12)] backdrop-blur-xl transition duration-200 ease-in-out`}
                >
                  <p className={`font-display text-3xl leading-none ${isDark ? 'text-white' : 'text-serene-ink'}`}>{item.title}</p>
                  <p className={`mt-2 text-2xl font-semibold ${isDark ? 'text-theme-accent' : 'text-serene-primary'}`}>{getPatternLabel(item)}</p>
                  <p className={`mt-1 text-base ${isDark ? 'text-white/60' : 'text-serene-muted'}`}>{getPurpose(item.id)}</p>
                  <div className={`mt-8 flex items-center justify-between ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>
                    <span className="text-xl">{Math.round(item.duration_sec / 60)} phút</span>
                    <Settings className="h-5 w-5" />
                  </div>
                </motion.button>
              ))}
            </section>

            <section className={`mt-6 flex items-center justify-between rounded-3xl border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/35 bg-white/65'} p-5 backdrop-blur-xl`}>
              <div>
                <h3 className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>Khởi động</h3>
                <p className={`mt-2 max-w-md text-base ${isDark ? 'text-white/60' : 'text-serene-muted'}`}>
                  Tìm hiểu cách thức hoạt động của từng bài tập thở và nhận những lời khuyên hữu ích để thực hành.
                </p>
              </div>
              <div className={`flex h-24 w-24 items-center justify-center rounded-3xl ${isDark ? 'bg-white/10' : 'bg-serene-primary/15'} text-3xl`}>🌬️</div>
            </section>
          </section>
        ) : (
          <section className={`flex min-h-[calc(100vh-5rem)] flex-col rounded-4xl border ${isDark ? 'border-white/10 bg-black/40' : 'border-white/40 bg-serene-bg/75'} p-5 shadow-md backdrop-blur-xl md:p-8`}>
            <header className="flex items-center justify-between">
              <button
                type="button"
                onClick={backToHub}
                className={`flex h-11 w-11 items-center justify-center rounded-full border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/50 bg-white/70'} ${isDark ? 'text-white' : 'text-serene-ink'} backdrop-blur-md transition duration-200 ease-in-out hover:bg-white/10`}
                aria-label="Quay lại danh sách bài thở"
              >
                <X className="h-5 w-5" />
              </button>
              <p className={`font-display text-2xl ${isDark ? 'text-white' : 'text-serene-ink'} md:text-3xl`}>{exercise.title}</p>
              <button
                type="button"
                onClick={resetExercise}
                className={`rounded-full border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/50 bg-white/70'} px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] ${isDark ? 'text-white/60' : 'text-serene-muted'} transition duration-200 ease-in-out hover:bg-white/10`}
              >
                Reset
              </button>
            </header>

            <main className="flex flex-1 flex-col items-center justify-center py-10 text-center">
              <motion.div
                animate={{ scale: isRunning ? phase.scale : 1 }}
                transition={{ duration: 1.1, ease: 'easeInOut' }}
                className={`relative flex h-56 w-56 items-center justify-center rounded-full ${isDark ? 'bg-white/5' : 'bg-white/45'} shadow-[0_0_80px_rgba(111,164,180,0.28)] md:h-72 md:w-72`}
              >
                <div className={`absolute inset-8 rounded-full ${isDark ? 'bg-white/5' : 'bg-white/55'}`} />
                <div className={`absolute inset-16 rounded-full ${isDark ? 'bg-white/5' : 'bg-white/75'}`} />
                <div className={`relative flex h-28 w-28 items-center justify-center rounded-full ${isDark ? 'bg-theme-accent' : 'bg-serene-primary/85'}`}>
                  <Waves className="h-9 w-9 text-white" />
                </div>
              </motion.div>

              <div className="mt-8">
                <p className={`font-display text-3xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>
                  {isDone ? 'Hoàn thành' : `${phase.label} (${phase.count})`}
                </p>
                <div className="mt-4 flex justify-center gap-2">
                  {exercise.steps.slice(0, 4).map((_, index) => (
                    <span
                      key={index}
                      className={`h-2 w-2 rounded-full ${index === phase.stepIndex && !isDone ? (isDark ? 'bg-theme-accent' : 'bg-serene-primary') : (isDark ? 'bg-white/10' : 'bg-serene-outline/30')}`}
                    />
                  ))}
                </div>
              </div>

              <div className="mt-10 w-full max-w-2xl">
                <div className={`h-2 overflow-hidden rounded-full ${isDark ? 'bg-white/5' : 'bg-white/65'}`}>
                  <div className={`h-full rounded-full ${isDark ? 'bg-theme-accent' : 'bg-serene-primary'} transition-all duration-300 ease-in-out`} style={{ width: `${progress}%` }} />
                </div>
                <div className={`mt-5 grid grid-cols-3 gap-4 ${isDark ? 'text-white' : 'text-serene-ink'}`}>
                  {exercise.pattern ? (
                    <>
                      <div className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/45 bg-white/78'} px-5 py-4`}><p className={`text-xs font-bold uppercase ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>Hít vào</p><p className="mt-1 font-display text-2xl">{exercise.pattern.inhale}s</p></div>
                      <div className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/45 bg-white/78'} px-5 py-4`}><p className={`text-xs font-bold uppercase ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>Giữ</p><p className="mt-1 font-display text-2xl">{exercise.pattern.hold}s</p></div>
                      <div className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/45 bg-white/78'} px-5 py-4`}><p className={`text-xs font-bold uppercase ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>Thở ra</p><p className="mt-1 font-display text-2xl">{exercise.pattern.exhale}s</p></div>
                    </>
                  ) : (
                    exercise.steps.slice(0, 3).map((step, index) => (
                      <div key={step} className={`rounded-3xl border ${isDark ? 'border-white/10 bg-white/5' : 'border-white/45 bg-white/78'} px-5 py-4`}>
                        <p className={`text-xs font-bold uppercase ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>Bước {index + 1}</p>
                        <p className="mt-1 text-xs leading-relaxed">{step}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <motion.button
                type="button"
                onClick={() => (isDone ? resetExercise() : setIsRunning((value) => !value))}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className={`mt-9 flex h-20 w-20 items-center justify-center rounded-full ${isDark ? 'bg-theme-accent' : 'bg-serene-primary'} text-white shadow-[0_16px_40px_rgba(111,164,180,0.35)]`}
                aria-label={isRunning ? 'Tạm dừng' : 'Bắt đầu'}
              >
                {isRunning ? <Pause className="h-8 w-8 fill-current" /> : <Play className="ml-1 h-9 w-9 fill-current" />}
              </motion.button>

              <p className={`mt-5 text-sm ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>
                {isDone ? 'Bạn đã hoàn thành phiên này. Cơ thể có thể cần vài giây để nhận ra sự dịu lại.' : `Còn lại ${formatTime(remaining)} · ${exercise.description}`}
              </p>
            </main>

            <aside className="grid gap-3 pb-3 md:grid-cols-3">
              {exercises.map((item) => (
                <motion.button
                  key={item.id}
                  type="button"
                  onClick={() => startExercise(item.id)}
                  whileHover={{ y: -2 }}
                  transition={{ duration: 0.2, ease: 'easeInOut' }}
                  className={`rounded-3xl border px-5 py-4 text-left backdrop-blur-xl transition duration-200 ease-in-out ${item.id === exercise.id
                      ? `${isDark ? 'border-theme-accent bg-white/10 shadow-[0_8px_18px_rgba(111,164,180,0.15)]' : 'border-serene-primary/45 bg-white/82 shadow-[0_8px_18px_rgba(111,164,180,0.15)]'}`
                      : `${isDark ? 'border-white/10 bg-white/5 hover:bg-white/10' : 'border-white/35 bg-white/65 hover:bg-white/78'}`
                    }`}
                >
                  <p className={`font-display text-xl ${isDark ? 'text-white' : 'text-serene-ink'}`}>{item.title}</p>
                  <p className={`mt-1 text-xs ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>{Math.round(item.duration_sec / 60)} phút · {item.type.replaceAll('_', ' ')}</p>
                </motion.button>
              ))}
            </aside>
          </section>
        )}
      </div>
    </div>
  )
}
