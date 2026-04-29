import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Pause, Play, Settings, Waves, X } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ocean from '../../assets/bg-reflect.png'
import { ROUTE_PATHS } from '../../routes/paths'
import { exerciseService, FALLBACK_EXERCISES, findFallbackExercise, type ExerciseItem } from '../../services/exerciseService'

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
    if (!item.pattern) return 'Set your own pattern'
    const parts = [item.pattern.inhale, item.pattern.hold, item.pattern.exhale]
    if (item.pattern.hold2 && item.pattern.hold2 > 0) parts.push(item.pattern.hold2)
    return parts.join('-')
  }

  const getPurpose = (id: string) => {
    if (id === 'box_breath') return 'Relaxation'
    if (id === 'breath_478') return 'Sleep'
    if (id === 'equal_breath') return 'Focus'
    if (id === 'custom_breath') return 'Custom'
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
    <div className="h-screen overflow-hidden rounded-xl text-serene sm:-m-8 lg:-m-12">
      <div className='absolute inset-0'>
        <img src={ocean} alt="" className=" inset-0 h-full w-full object-cover" />
      </div>


      <div className="relative px-6 py-8 md:px-12">
        {isHubMode ? (
          <div className="mx-auto w-full max-w-3xl">
            <header className="mb-8 flex items-center justify-between">
              <button
                type="button"
                onClick={() => navigate(ROUTE_PATHS.resources)}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-white/20 text-white backdrop-blur-md transition hover:bg-white/30"
                aria-label="Quay lại thư viện"
              >
                <X className="h-5 w-5" />
              </button>
              <h1 className="font-display text-4xl text-white/90">Breathing exercises</h1>
              <span className="h-11 w-11" />
            </header>

            <h2 className="mb-7 text-5xl font-semibold leading-tight text-white/95">
              Choose a breathing
              <br />
              exercise to practise.
            </h2>

            <section className="grid gap-4 sm:grid-cols-2">
              {hubCards.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => startExercise(item.id)}
                  className="rounded-3xl bg-[#4b4297]/90 p-5 text-left shadow-[0_12px_28px_rgba(0,0,0,0.2)] transition hover:brightness-110"
                >
                  <p className="font-display text-4xl leading-none text-white">{item.title}</p>
                  <p className="mt-2 text-3xl font-semibold text-white/90">{getPatternLabel(item)}</p>
                  <p className="mt-1 text-xl text-white/70">{getPurpose(item.id)}</p>
                  <div className="mt-8 flex items-center justify-between text-white/70">
                    <span className="text-xl">{Math.round(item.duration_sec / 60)} mins</span>
                    <Settings className="h-5 w-5" />
                  </div>
                </button>
              ))}
            </section>

            <section className="mt-6 flex items-center justify-between rounded-3xl bg-[#27235f]/90 p-5">
              <div>
                <h3 className="text-3xl font-semibold">Before you get started</h3>
                <p className="mt-2 max-w-md text-xl text-white/75">
                  Learn how each breathing exercise works and get tips to help you practise.
                </p>
              </div>
              <div className="h-24 w-24 rounded-3xl bg-[#75c6ed]" />
            </section>
          </div>
        ) : (
          <div className="flex min-h-[calc(100vh-5rem)] flex-col">
            <header className="flex items-center justify-between">
              <button
                type="button"
                onClick={backToHub}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-white/20 text-white backdrop-blur-md transition hover:bg-white/30"
                aria-label="Quay lại danh sách bài thở"
              >
                <X className="h-5 w-5" />
              </button>
              <p className="font-display text-3xl text-white/85">{exercise.title}</p>
              <button
                type="button"
                onClick={resetExercise}
                className="rounded-full bg-white/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-white/80"
              >
                Reset
              </button>
            </header>

            <main className="flex flex-1 flex-col items-center justify-center py-10 text-center">
              <motion.div
                animate={{ scale: isRunning ? phase.scale : 1 }}
                transition={{ duration: 1.1, ease: 'easeInOut' }}
                className="relative flex h-56 w-56 items-center justify-center rounded-full bg-white/12 shadow-[0_0_80px_rgba(188,233,231,0.35)] md:h-72 md:w-72"
              >
                <div className="absolute inset-8 rounded-full bg-white/20" />
                <div className="absolute inset-16 rounded-full bg-white/35" />
                <div className="relative flex h-28 w-28 items-center justify-center rounded-full bg-serene-primary/85">
                  <Waves className="h-9 w-9 text-white/85" />
                </div>
              </motion.div>

              <div className="mt-8">
                <p className="font-display text-3xl text-white/90">
                  {isDone ? 'Hoàn thành' : `${phase.label} (${phase.count})`}
                </p>
                <div className="mt-4 flex justify-center gap-2">
                  {exercise.steps.slice(0, 4).map((_, index) => (
                    <span
                      key={index}
                      className={`h-2 w-2 rounded-full ${index === phase.stepIndex && !isDone ? 'bg-white' : 'bg-white/35'}`}
                    />
                  ))}
                </div>
              </div>

              <div className="mt-10 w-full max-w-2xl">
                <div className="h-2 overflow-hidden rounded-full bg-white/45">
                  <div className="h-full rounded-full bg-white transition-all" style={{ width: `${progress}%` }} />
                </div>
                <div className="mt-5 grid grid-cols-3 gap-4 text-serene-ink">
                  {exercise.pattern ? (
                    <>
                      <div className="rounded-3xl bg-white/75 px-5 py-4"><p className="text-xs font-bold uppercase">Hít vào</p><p className="mt-1 font-display text-2xl">{exercise.pattern.inhale}s</p></div>
                      <div className="rounded-3xl bg-white/75 px-5 py-4"><p className="text-xs font-bold uppercase">Giữ</p><p className="mt-1 font-display text-2xl">{exercise.pattern.hold}s</p></div>
                      <div className="rounded-3xl bg-white/75 px-5 py-4"><p className="text-xs font-bold uppercase">Thở ra</p><p className="mt-1 font-display text-2xl">{exercise.pattern.exhale}s</p></div>
                    </>
                  ) : (
                    exercise.steps.slice(0, 3).map((step, index) => (
                      <div key={step} className="rounded-3xl bg-white/75 px-5 py-4">
                        <p className="text-xs font-bold uppercase">Bước {index + 1}</p>
                        <p className="mt-1 text-xs leading-relaxed">{step}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => (isDone ? resetExercise() : setIsRunning((value) => !value))}
                className="mt-9 flex h-20 w-20 items-center justify-center rounded-full bg-serene-primary text-white shadow-[0_20px_50px_rgba(0,0,0,0.22)] transition hover:scale-105"
                aria-label={isRunning ? 'Tạm dừng' : 'Bắt đầu'}
              >
                {isRunning ? <Pause className="h-8 w-8 fill-current" /> : <Play className="ml-1 h-9 w-9 fill-current" />}
              </button>

              <p className="mt-5 text-sm text-white/75">
                {isDone ? 'Bạn đã hoàn thành phiên này. Cơ thể có thể cần vài giây để nhận ra sự dịu lại.' : `Còn lại ${formatTime(remaining)} · ${exercise.description}`}
              </p>
            </main>

            <aside className="grid gap-3 pb-3 md:grid-cols-3">
              {exercises.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => startExercise(item.id)}
                  className={`rounded-3xl border px-5 py-4 text-left backdrop-blur-xl transition ${item.id === exercise.id ? 'border-white/70 bg-white/25' : 'border-white/20 bg-white/10 hover:bg-white/18'
                    }`}
                >
                  <p className="font-display text-xl">{item.title}</p>
                  <p className="mt-1 text-xs text-white/70">{Math.round(item.duration_sec / 60)} phút · {item.type.replaceAll('_', ' ')}</p>
                </button>
              ))}
            </aside>
          </div>
        )}
      </div>
    </div>
  )
}
