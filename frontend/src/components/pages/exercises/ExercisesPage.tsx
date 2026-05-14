import { useEffect, useMemo, useState, useRef } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Accessibility, Focus, LayoutGrid, Sparkles, Waves, Wind, Volume2, VolumeX, Pause, Play, ArrowLeft } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ROUTE_PATHS } from '../../../routes/paths'
import { useThemeContext } from '../../../contexts/ThemeContext'
import dayBackground from '../../../assets/motion/serene-landing-day-welcome.gif'
import nightBackground from '../../../assets/motion/serene-landing-night-welcome.gif'
import BackgroundLayer from './BackgroundLayer'
import ExerciseHero from './ExerciseHero'
import ExerciseFilterChips, { type ExerciseTabId } from './ExerciseFilterChips'
import ExerciseCard, { type ExerciseCardData } from './ExerciseCard'
import { useAmbientSound } from './useAmbientSound'
import '../landing/landing.css'

const AMBIENT_AUDIO_SRC = '/audio/ambient-water-birds-leaves.mp3'

const EXERCISES: ExerciseCardData[] = [
  {
    id: 'box_breath',
    type: 'breathing_exercise',
    title: 'Hít thở nhịp 4',
    durationLabel: '5 phút',
    description: 'Nhịp 4-4-4-4 giúp bạn lấy lại bình tĩnh.',
    structure: '4-4-4-4',
    recommendedFor: 'Khi căng thẳng hoặc cần bình tĩnh',
    tone: 'Ổn định',
    gradient: 'var(--leaf-green)',
    icon: Wind,
    audioSrc: '/audio/breath-4-4-4-4.mp3',
  },
  {
    id: 'breath_478',
    type: 'breathing_exercise',
    title: 'Hít thở sâu',
    durationLabel: '2 phút',
    description: 'Một bài ngắn để hít thở sâu, giảm cảm giác gấp gáp.',
    structure: '4-7-8',
    recommendedFor: 'Khi lo lắng, bồn chồn',
    tone: 'Làm dịu',
    gradient: 'var(--rain-blue)',
    icon: Waves,
    audioSrc: '/audio/breath-4-7-8.mp3',
  },
  {
    id: 'equal_breath',
    type: 'breathing_exercise',
    title: 'Hít thở đều',
    durationLabel: '5 phút',
    description: 'Giữ nhịp thở đều để cân bằng lại sự tập trung.',
    structure: '5-0-5',
    recommendedFor: 'Khi cần tập trung',
    tone: 'Tập trung',
    gradient: 'var(--yellow)',
    icon: Sparkles,
    audioSrc: '/audio/breath-5-0-5.mp3',
  },
  {
    id: 'grounding_54321',
    type: 'grounding_exercise',
    title: 'Neo hiện tại',
    durationLabel: '3 phút',
    description: 'Kéo sự tập trung về hiện tại bằng nhịp 5-4-3-2-1.',
    structure: '5-4-3-2-1',
    recommendedFor: 'Khi tâm trí chạy quá nhanh',
    tone: 'Bình tâm',
    gradient: 'var(--orange)',
    icon: Focus,
  },
  {
    id: 'body_scan',
    type: 'body_scan',
    title: 'Thiền định',
    durationLabel: '5 phút',
    description: 'Buông lỏng từng vùng cơ thể sau một ngày quá tải.',
    structure: 'Thả lỏng cơ tứ chi chân',
    recommendedFor: 'Khi mệt hoặc khó ngủ',
    tone: 'Tĩnh tâm, thả lỏng cơ thể',
    gradient: 'var(--mint)',
    icon: Accessibility,
    audioSrc: '/audio/body-scan-5min.mp3',
  },
]

const TABS: { id: ExerciseTabId; label: string; icon: typeof LayoutGrid }[] = [
  { id: 'all', label: 'Tất cả', icon: LayoutGrid },
  { id: 'breathing_exercise', label: 'Hít thở', icon: Wind },
  { id: 'grounding_exercise', label: 'Bình tâm', icon: Focus },
  { id: 'body_scan', label: 'Quét cơ thể', icon: Accessibility },
]

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function getActiveExercise(selectedId: string | null) {
  return EXERCISES.find((exercise) => exercise.id === selectedId) ?? EXERCISES[0]
}

export function ExercisesPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { effectiveTheme } = useThemeContext()
  const ambient = useAmbientSound(AMBIENT_AUDIO_SRC)
  const reduceMotion = useReducedMotion()

  const isDark = effectiveTheme === 'dark'
  const [activeTab, setActiveTab] = useState<ExerciseTabId>('all')
  const [elapsed, setElapsed] = useState(0)
  const [isRunning, setIsRunning] = useState(false)

  const selectedFromQuery = searchParams.get('exercise')
  const activeExercise = useMemo(() => getActiveExercise(selectedFromQuery), [selectedFromQuery])
  const isHubMode = !selectedFromQuery

  const exerciseAudioRef = useRef<HTMLAudioElement | null>(null)

  const filteredExercises = useMemo(() => {
    if (activeTab === 'all') return EXERCISES
    return EXERCISES.filter((exercise) => exercise.type === activeTab)
  }, [activeTab])

  const remaining = Math.max(0, 300 - elapsed)
  const progress = Math.min(100, Math.round((elapsed / 300) * 100))
  const currentBackground = isDark ? nightBackground : dayBackground

  useEffect(() => {
    if (!isRunning || !selectedFromQuery) {
      if (exerciseAudioRef.current) {
        exerciseAudioRef.current.pause()
      }
      return undefined
    }

    const timer = window.setInterval(() => {
      setElapsed((value) => Math.min(300, value + 1))
    }, 1000)

    if (activeExercise.audioSrc) {
      if (!exerciseAudioRef.current) {
        exerciseAudioRef.current = new Audio(activeExercise.audioSrc)
      } else if (exerciseAudioRef.current.src !== window.location.origin + activeExercise.audioSrc) {
        exerciseAudioRef.current.src = activeExercise.audioSrc
      }
      void exerciseAudioRef.current.play().catch(console.error)
    }

    return () => {
      window.clearInterval(timer)
      if (exerciseAudioRef.current) {
        exerciseAudioRef.current.pause()
      }
    }
  }, [isRunning, selectedFromQuery, activeExercise])

  useEffect(() => {
    // Coordinate ambient sound with exercise audio
    if (isRunning && activeExercise.audioSrc) {
      // Lower ambient volume or pause if needed
      // Assuming useAmbientSound manages its own audio element
      // For now, we'll just focus on playing the exercise audio
    }
  }, [isRunning, activeExercise])

  const startExercise = (id: string) => {
    setSearchParams({ exercise: id })
    setElapsed(0)
    setIsRunning(false)
  }

  const backToHub = () => {
    setSearchParams({})
    setElapsed(0)
    setIsRunning(false)
    if (exerciseAudioRef.current) {
      exerciseAudioRef.current.pause()
      exerciseAudioRef.current = null
    }
  }

  const toggleRunning = () => {
    setIsRunning((prev) => !prev)
  }

  return (
    <div className={`serene-landing relative min-h-screen overflow-hidden ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>
      <BackgroundLayer src={currentBackground} mode={isDark ? 'dark' : 'light'} />

      <div className="relative z-10 mx-auto max-w-[1040px] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
        {isHubMode ? (
          <motion.main
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="space-y-5"
          >
            <ExerciseHero
              onBack={() => navigate(ROUTE_PATHS.resources)}
              title="Chọn một bài ngắn để thở chậm lại, thả lỏng cơ thể."
              subtitle="Mỗi bài được thiết kế để bắt đầu thật nhẹ. Bạn chỉ cần chọn một trạng thái gần nhất, rồi bấm bắt đầu."
            />

            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <ExerciseFilterChips tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
                
                {/* Compact Ambient Control Bar */}
                <div className="flex items-center gap-3 border-2 px-3 py-1.5 bg-theme-surface shadow-[4px_4px_0_rgba(0,0,0,0.1)]" style={{ borderRadius: '4px', borderColor: 'var(--border-soft)' }}>
                  <span className="pixel-label text-[12px] font-bold tracking-widest opacity-80" style={{ color: isDark ? 'var(--mint)' : '#5F7F68' }}>
                    Âm thanh nền
                  </span>
                  <div className="h-4 w-[2px] bg-current opacity-20" />
                  <button
                    type="button"
                    onClick={ambient.toggle}
                    className="flex h-8 w-8 items-center justify-center border-2 transition-all active:scale-90"
                    style={{ borderRadius: '2px', background: ambient.isPlaying ? 'var(--mint)' : 'transparent', borderColor: 'var(--mint)', color: ambient.isPlaying ? '#07111f' : 'var(--mint)' }}
                    aria-label={ambient.isPlaying ? 'Tắt âm thanh' : 'Bật âm thanh'}
                  >
                    {ambient.isPlaying ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <section aria-label="Danh sách bài tập" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 py-3!">
                <AnimatePresence mode="popLayout">
                  {filteredExercises.map((exercise, index) => (
                    <ExerciseCard key={exercise.id} exercise={exercise} onStart={startExercise} index={index} />
                  ))}
                </AnimatePresence>
              </section>
            </div>
          </motion.main>
        ) : (
          <motion.main
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className={`mx-auto max-w-4xl overflow-hidden rounded-[32px] border shadow-[0_20px_60px_rgba(16,35,31,0.15)] backdrop-blur-md bg-theme-surface/80`}
          >
            <header className="flex items-center justify-between border-b border-white/10 px-6 py-4 sm:px-8">
              <button
                type="button"
                onClick={backToHub}
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition-all hover:scale-105 ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8] hover:bg-white/10' : 'border-[#5F7F68]/20 bg-white/40 text-[#24352D] hover:bg-white/60'}`}
              >
                <ArrowLeft className="h-4 w-4" />
                Thoát
              </button>

              <div className="text-center">
                <p className={`text-[10px] font-bold uppercase tracking-[0.2em] ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>
                  {activeExercise.tone}
                </p>
                <h1 className={`text-xl font-bold tracking-tight sm:text-2xl ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>
                  {activeExercise.title}
                </h1>
              </div>

              <button
                type="button"
                onClick={() => {
                  setElapsed(0)
                  setIsRunning(false)
                }}
                className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition-all hover:scale-105 ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8] hover:bg-white/10' : 'border-[#5F7F68]/20 bg-white/40 text-[#24352D] hover:bg-white/60'}`}
              >
                Làm lại
              </button>
            </header>

            <div className="px-6 py-10 sm:px-12 sm:py-16">
              <section className="flex flex-col items-center text-center">
                <div className="relative mb-12 flex h-[280px] w-full items-center justify-center sm:h-[360px]">
                  <motion.div
                    animate={reduceMotion ? { scale: 1, opacity: 0.25 } : {
                      scale: isRunning ? [1, 1.1, 1] : 1,
                      opacity: isRunning ? [0.3, 0.6, 0.3] : 0.25,
                    }}
                    transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                    className={`absolute h-[240px] w-[240px] rounded-full border-2 sm:h-[320px] sm:w-[320px] ${isDark ? 'border-[#F4D28A]/20' : 'border-[#5F7F68]/20'}`}
                  />
                  <motion.div
                    animate={reduceMotion ? { scale: 1, opacity: 0.15 } : {
                      scale: isRunning ? [1, 1.2, 1] : 1,
                      opacity: isRunning ? [0.15, 0.3, 0.15] : 0.15,
                    }}
                    transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                    className={`absolute h-[280px] w-[280px] rounded-full border sm:h-[360px] sm:w-[360px] ${isDark ? 'border-[#F4D28A]/10' : 'border-[#5F7F68]/10'}`}
                  />

                  <motion.div
                    animate={reduceMotion ? { scale: 1 } : { scale: isRunning ? [1, 1.05, 1] : 1 }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                    className={`relative flex h-[180px] w-[180px] items-center justify-center rounded-full shadow-2xl backdrop-blur-xl sm:h-[240px] sm:w-[240px] ${isDark ? 'bg-white/10' : 'bg-white/30'}`}
                  >
                    <div className={`flex h-32 w-32 items-center justify-center rounded-full sm:h-44 sm:w-44 ${isDark ? 'bg-white/10 text-[#F4D28A]' : 'bg-white/60 text-[#5F7F68]'}`}>
                      <Waves className={`h-16 w-16 ${isRunning ? 'animate-pulse' : ''}`} />
                    </div>
                  </motion.div>
                </div>

                <div className="mb-10 space-y-4">
                  <motion.p
                    key={isRunning ? 'running' : 'idle'}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`text-2xl font-bold tracking-tight sm:text-3xl ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}
                  >
                    {isRunning ? 'Đang hướng dẫn bạn...' : 'Sẵn sàng để bắt đầu?'}
                  </motion.p>
                  <p className={`max-w-md text-sm leading-relaxed font-medium ${isDark ? 'text-[#F4E8C8]/70' : 'text-[#24352D]/70'}`}>
                    {activeExercise.description}
                  </p>
                </div>

                <div className="mb-12 w-full max-w-md space-y-4">
                  <div className={`h-2.5 overflow-hidden rounded-full ${isDark ? 'bg-white/10' : 'bg-[#5F7F68]/10'}`}>
                    <motion.div
                      className={`h-full rounded-full ${isDark ? 'bg-[#F4D28A]' : 'bg-[#5F7F68]'}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <div className={`flex justify-between text-[11px] font-bold uppercase tracking-widest ${isDark ? 'text-[#F4E8C8]/50' : 'text-[#24352D]/50'}`}>
                    <span>Đã qua: {formatTime(elapsed)}</span>
                    <span>Còn lại: {formatTime(remaining)}</span>
                  </div>
                </div>

                <motion.button
                  type="button"
                  onClick={toggleRunning}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`flex h-24 w-24 items-center justify-center rounded-full shadow-xl transition-all ${isRunning ? (isDark ? 'bg-[#F4D28A] text-[#10231F]' : 'bg-[#24352D] text-white') : (isDark ? 'bg-white/20 text-[#F4E8C8]' : 'bg-[#5F7F68] text-white')}`}
                >
                  {isRunning ? <Pause className="h-10 w-10 fill-current" /> : <Play className="ml-2 h-10 w-10 fill-current" />}
                </motion.button>
              </section>

              <div className="mt-20 grid gap-6 sm:grid-cols-3">
                <div className={`rounded-3xl border p-6 ${isDark ? 'border-white/10 bg-white/5' : 'border-[#5F7F68]/20 bg-white/40'}`}>
                  <p className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>Cấu trúc</p>
                  <p className={`mt-2 text-lg font-bold ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>{activeExercise.structure}</p>
                </div>
                <div className={`rounded-3xl border p-6 ${isDark ? 'border-white/10 bg-white/5' : 'border-[#5F7F68]/20 bg-white/40'}`}>
                  <p className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>Thời lượng</p>
                  <p className={`mt-2 text-lg font-bold ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>{activeExercise.durationLabel}</p>
                </div>
                <div className={`rounded-3xl border p-6 ${isDark ? 'border-white/10 bg-white/5' : 'border-[#5F7F68]/20 bg-white/40'}`}>
                  <p className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>Âm thanh</p>
                  <div className="mt-2 flex items-center gap-3">
                    <button 
                      onClick={ambient.toggle}
                      className={`flex h-8 w-8 items-center justify-center rounded-full ${isDark ? 'bg-white/10 text-[#F4E8C8]' : 'bg-[#5F7F68]/10 text-[#5F7F68]'}`}
                    >
                      {ambient.isPlaying ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                    </button>
                    <span className={`text-sm font-bold ${isDark ? 'text-[#F4E8C8]' : 'text-[#24352D]'}`}>Nền</span>
                  </div>
                </div>
              </div>

              <div className={`mt-6 rounded-3xl border p-6 text-center text-sm font-medium leading-relaxed italic ${isDark ? 'border-white/10 bg-white/5 text-[#F4E8C8]/60' : 'border-[#5F7F68]/10 bg-white/20 text-[#24352D]/60'}`}>
                "Giữ vai mềm, thả lỏng hàm và để hơi thở đi chậm hơn một chút so với nhịp bình thường."
              </div>
            </div>
          </motion.main>
        )}
      </div>
    </div>
  )
}
