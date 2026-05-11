import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Accessibility, Focus, LayoutGrid, Leaf, Sparkles, Waves, Wind, Volume2, VolumeX, Pause, Play, ArrowLeft } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ROUTE_PATHS } from '../../routes/paths'
import { useThemeContext } from '../../contexts/ThemeContext'
import dayBackground from '../../assets/motion/serene-landing-day-welcome.gif'
import nightBackground from '../../assets/motion/serene-landing-night-welcome.gif'
import BackgroundLayer from './exercises/BackgroundLayer'
import ExerciseHero from './exercises/ExerciseHero'
import ExerciseFilterChips, { type ExerciseTabId } from './exercises/ExerciseFilterChips'
import ExerciseCard, { type ExerciseCardData } from './exercises/ExerciseCard'
import { useAmbientSound } from './exercises/useAmbientSound'

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
    gradient: 'from-[#5F7F68]/20 via-[#F4E8C8]/14 to-transparent',
    icon: Wind,
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
    gradient: 'from-[#E8B38E]/24 via-[#F4E8C8]/14 to-transparent',
    icon: Waves,
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
    gradient: 'from-[#10231F]/12 via-[#5F7F68]/14 to-transparent',
    icon: Sparkles,
  },
  {
    id: 'grounding_54321',
    type: 'grounding_exercise',
    title: 'Neo hiện tại',
    durationLabel: '3 phút',
    description: 'Kéo sự chú ý về quanh bạn bằng nhịp 5-4-3-2-1.',
    structure: '5-4-3-2-1',
    recommendedFor: 'Khi tâm trí chạy quá nhanh',
    tone: 'Bình tâm',
    gradient: 'from-[#5F7F68]/18 via-[#F4E8C8]/12 to-transparent',
    icon: Focus,
  },
  {
    id: 'body_scan',
    type: 'body_scan',
    title: 'Thiền định',
    durationLabel: '5 phút',
    description: 'Buông lỏng từng vùng cơ thể sau một ngày quá tải.',
    structure: 'Thả lỏng cơ tứ chi chân, loại bỏ suy nghĩ ra khỏi đầu',
    recommendedFor: 'Khi mệt hoặc khó ngủ',
    tone: 'Tĩnh tâm, thả lỏng cơ thể',
    gradient: 'from-[#F4D28A]/20 via-[#F4E8C8]/12 to-transparent',
    icon: Accessibility,
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

  const filteredExercises = useMemo(() => {
    if (activeTab === 'all') return EXERCISES
    return EXERCISES.filter((exercise) => exercise.type === activeTab)
  }, [activeTab])

  const remaining = Math.max(0, 300 - elapsed)
  const progress = Math.min(100, Math.round((elapsed / 300) * 100))
  const currentBackground = isDark ? nightBackground : dayBackground

  useEffect(() => {
    if (!isRunning || !selectedFromQuery) return undefined
    const timer = window.setInterval(() => {
      setElapsed((value) => Math.min(300, value + 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [isRunning, selectedFromQuery])

  const startExercise = (id: string) => {
    setSearchParams({ exercise: id })
    setElapsed(0)
    setIsRunning(false)
  }

  const backToHub = () => {
    setSearchParams({})
    setElapsed(0)
    setIsRunning(false)
  }

  return (
    <div className="relative min-h-screen overflow-hidden text-[#24352D] dark:text-[#F4E8C8]">
      <BackgroundLayer src={currentBackground} mode={isDark ? 'dark' : 'light'} />

      <div className="relative z-10 mx-auto max-w-[1040px] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
        {isHubMode ? (
          <motion.main
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className="space-y-6"
          >
            <ExerciseHero
              onBack={() => navigate(ROUTE_PATHS.resources)}
              title="Chọn một bài ngắn để thở chậm lại, thả lỏng cơ thể."
              subtitle="Mỗi bài được thiết kế để bắt đầu thật nhẹ. Bạn chỉ cần chọn một trạng thái gần nhất, rồi bấm bắt đầu."
            />

            <section className="grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
              <aside className="rounded-[28px] border border-white/35 bg-[#F8F1DC]/88 p-6 shadow-[0_18px_40px_rgba(16,35,31,0.10)] backdrop-blur-sm dark:border-white/15 dark:bg-[#10231F]/78 sm:p-8">
                <div className="flex items-start gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#5F7F68]/15 text-[#5F7F68] dark:bg-white/10 dark:text-[#F4E8C8]">
                    <Volume2 className="h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-[#5F7F68] dark:text-[#F4D28A]">
                      Âm thanh nền
                    </p>
                    <h2 className="mt-1 text-xl font-semibold text-[#24352D] dark:text-[#F4E8C8]">
                      Nước nhẹ, chim nhỏ, lá khẽ
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-[#24352D]/78 dark:text-[#F4E8C8]/78">
                      Trang sẽ cố phát âm thanh nền ngay khi vào. Nếu trình duyệt chặn, chỉ cần bấm mở âm thanh.
                    </p>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Chim chóc', icon: Sparkles },
                    { label: 'Lá cây', icon: Leaf },
                    { label: 'Tiếng nước', icon: Waves },
                  ].map((item) => {
                    const Icon = item.icon
                    return (
                      <div
                        key={item.label}
                        className="rounded-[18px] border border-white/30 bg-white/30 px-3 py-3 text-center text-sm text-[#24352D] dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                      >
                        <Icon className="mx-auto h-4 w-4 opacity-80" />
                        <p className="mt-2">{item.label}</p>
                      </div>
                    )
                  })}
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={ambient.toggle}
                    className="inline-flex items-center gap-2 rounded-full bg-[#5F7F68] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2"
                    aria-label={ambient.isPlaying ? 'Tắt âm thanh nền' : 'Bật âm thanh nền'}
                  >
                    {ambient.isPlaying ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                    {ambient.isPlaying ? 'Đang phát' : 'Bật âm thanh'}
                  </button>
                  <button
                    type="button"
                    onClick={() => ambient.setMuted(!ambient.isMuted)}
                    className="rounded-full border border-white/30 bg-white/25 px-4 py-2.5 text-sm font-medium text-[#24352D] transition-colors hover:bg-white/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                    aria-label={ambient.isMuted ? 'Bỏ tắt tiếng' : 'Tắt tiếng'}
                  >
                    {ambient.isMuted ? 'Bỏ tắt tiếng' : 'Tắt tiếng'}
                  </button>
                  <span className="text-xs text-[#24352D]/60 dark:text-[#F4E8C8]/65">
                    {ambient.hasLoaded ? 'Âm thanh đã sẵn sàng.' : ambient.autoplayBlocked ? 'Trình duyệt cần bạn chạm để phát.' : 'Đang nạp âm thanh...'}
                  </span>
                </div>
              </aside>

              <div className="space-y-4">
                <ExerciseFilterChips tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
                <section aria-label="Danh sách bài tập" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <AnimatePresence mode="popLayout">
                    {filteredExercises.map((exercise, index) => (
                      <ExerciseCard key={exercise.id} exercise={exercise} onStart={startExercise} index={index} />
                    ))}
                  </AnimatePresence>
                </section>
              </div>
            </section>
          </motion.main>
        ) : (
          <motion.main
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="rounded-[28px] border border-white/35 bg-[#F8F1DC]/88 p-4 shadow-[0_18px_40px_rgba(16,35,31,0.10)] backdrop-blur-sm dark:border-white/15 dark:bg-[#10231F]/78 sm:p-6 lg:p-8"
          >
            <header className="flex flex-wrap items-center justify-between gap-4">
              <button
                type="button"
                onClick={backToHub}
                className="inline-flex h-11 items-center gap-2 rounded-full border border-white/35 bg-white/25 px-4 text-sm font-medium text-[#24352D] transition-colors hover:bg-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                aria-label="Quay lại"
              >
                <ArrowLeft className="h-4 w-4" />
                Quay lại
              </button>

              <div className="text-center">
                <p className="text-[11px] font-medium uppercase tracking-[0.24em] text-[#5F7F68] dark:text-[#F4D28A]">
                  {activeExercise.tone}
                </p>
                <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#24352D] dark:text-[#F4E8C8] sm:text-3xl">
                  {activeExercise.title}
                </h1>
              </div>

              <button
                type="button"
                onClick={() => {
                  setElapsed(0)
                  setIsRunning(false)
                }}
                className="inline-flex h-11 items-center gap-2 rounded-full border border-white/35 bg-white/25 px-4 text-sm font-medium text-[#24352D] transition-colors hover:bg-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                aria-label="Làm lại bài tập"
              >
                Làm lại
              </button>
            </header>

            <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_0.9fr] lg:items-center">
              <section className="flex flex-col items-center text-center">
                <div className="relative flex h-[260px] w-full max-w-[340px] items-center justify-center sm:h-[320px] sm:max-w-[400px]">
                  <motion.div
                    animate={reduceMotion ? { scale: 1, opacity: 0.25 } : {
                      scale: isRunning ? [1, 1.04, 1] : 1,
                      opacity: isRunning ? [0.3, 0.5, 0.3] : 0.25,
                    }}
                    transition={{ duration: 3.6, repeat: Infinity, ease: 'easeInOut' }}
                    className="absolute inset-6 rounded-full border border-[#5F7F68]/30"
                  />
                  <motion.div
                    animate={reduceMotion ? { scale: 1, opacity: 0.16 } : {
                      scale: isRunning ? [1, 1.08, 1] : 1,
                      opacity: isRunning ? [0.18, 0.28, 0.18] : 0.16,
                    }}
                    transition={{ duration: 4.8, repeat: Infinity, ease: 'easeInOut' }}
                    className="absolute inset-0 rounded-full border border-[#5F7F68]/20"
                  />

                  <motion.div
                    animate={reduceMotion ? { scale: 1 } : { scale: isRunning ? [1, 1.06, 1] : 1 }}
                    transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
                    className="relative flex h-[180px] w-[180px] items-center justify-center rounded-full bg-white/25 shadow-[0_16px_38px_rgba(16,35,31,0.18)] backdrop-blur-md dark:bg-white/5 sm:h-[220px] sm:w-[220px]"
                  >
                    <div className="flex h-32 w-32 items-center justify-center rounded-full bg-white/40 text-[#5F7F68] dark:bg-white/10 dark:text-[#F4E8C8] sm:h-40 sm:w-40">
                      <Waves className="h-12 w-12" />
                    </div>
                  </motion.div>
                </div>

                <div className="mt-6 space-y-3">
                  <motion.p
                    key={isRunning ? 'running' : 'idle'}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-3xl font-semibold tracking-tight text-[#24352D] dark:text-[#F4E8C8] sm:text-4xl"
                  >
                    {isRunning ? 'Đang thở cùng bạn' : 'Đợi bạn bấm bắt đầu'}
                  </motion.p>
                  <p className="text-5xl font-light tabular-nums text-[#5F7F68] dark:text-[#F4D28A]">
                    {isRunning ? '•' : '0'}
                  </p>
                  <p className="max-w-lg text-sm leading-6 text-[#24352D]/78 dark:text-[#F4E8C8]/78">
                    {activeExercise.description}
                  </p>
                </div>

                <div className="mt-8 w-full max-w-md space-y-3">
                  <div className="h-2 overflow-hidden rounded-full bg-white/35 dark:bg-white/10">
                    <motion.div
                      className="h-full rounded-full bg-[#5F7F68]"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.35 }}
                    />
                  </div>
                  <div className="flex justify-between text-xs font-medium uppercase tracking-[0.22em] text-[#24352D]/55 dark:text-[#F4E8C8]/55">
                    <span>Đã qua: {formatTime(elapsed)}</span>
                    <span>Còn lại: {formatTime(remaining)}</span>
                  </div>
                </div>

                <motion.button
                  type="button"
                  onClick={() => setIsRunning((value) => !value)}
                  whileTap={{ scale: 0.96 }}
                  className={`mt-8 inline-flex h-20 w-20 items-center justify-center rounded-full text-white shadow-[0_18px_34px_rgba(16,35,31,0.20)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 ${isRunning ? 'bg-[#5F7F68]' : 'bg-[#24352D]'}`}
                  aria-label={isRunning ? 'Tạm dừng' : 'Bắt đầu'}
                >
                  {isRunning ? <Pause className="h-8 w-8" /> : <Play className="ml-1 h-8 w-8" />}
                </motion.button>
              </section>

              <aside className="space-y-4 rounded-[24px] border border-white/35 bg-white/20 p-5 backdrop-blur-sm dark:border-white/10 dark:bg-white/5 sm:p-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5F7F68]/12 text-[#5F7F68] dark:bg-white/10 dark:text-[#F4E8C8]">
                    <Waves className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-[#5F7F68] dark:text-[#F4D28A]">
                      Cấu trúc bài
                    </p>
                    <p className="mt-1 text-lg font-semibold text-[#24352D] dark:text-[#F4E8C8]">
                      {activeExercise.structure}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-[18px] border border-white/30 bg-white/20 p-4 text-[#24352D] dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]">
                    <p className="text-[11px] uppercase tracking-[0.22em] text-[#5F7F68] dark:text-[#F4D28A]">
                      Thời lượng
                    </p>
                    <p className="mt-2 text-xl font-semibold">{activeExercise.durationLabel}</p>
                  </div>
                  <div className="rounded-[18px] border border-white/30 bg-white/20 p-4 text-[#24352D] dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]">
                    <p className="text-[11px] uppercase tracking-[0.22em] text-[#5F7F68] dark:text-[#F4D28A]">
                      Phù hợp khi
                    </p>
                    <p className="mt-2 text-sm leading-6">{activeExercise.recommendedFor}</p>
                  </div>
                </div>

                <div className="rounded-[20px] border border-white/30 bg-white/20 p-4 text-sm leading-6 text-[#24352D]/82 dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]/82">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-[#5F7F68] dark:text-[#F4D28A]">
                    Gợi ý nhẹ
                  </p>
                  <p className="mt-2">
                    Giữ vai mềm, thả lỏng hàm và để hơi thở đi chậm hơn một chút so với nhịp bình thường.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {[ambient.isPlaying ? 'Âm thanh đang mở' : 'Âm thanh tĩnh', activeExercise.id === 'body_scan' ? 'Dành cho buổi tối' : 'Dùng vào lúc cần nhẹ lại'].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/30 bg-white/20 px-3 py-1 text-xs font-medium text-[#24352D] dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={ambient.toggle}
                    className="inline-flex items-center gap-2 rounded-full bg-[#5F7F68] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2"
                  >
                    {ambient.isPlaying ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                    {ambient.isPlaying ? 'Tạm dừng âm thanh' : 'Bật âm thanh'}
                  </button>
                  <button
                    type="button"
                    onClick={backToHub}
                    className="inline-flex items-center gap-2 rounded-full border border-white/35 bg-white/20 px-4 py-2.5 text-sm font-medium text-[#24352D] transition-colors hover:bg-white/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 dark:border-white/10 dark:bg-white/5 dark:text-[#F4E8C8]"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Về danh sách
                  </button>
                </div>
              </aside>
            </div>
          </motion.main>
        )}
      </div>
    </div>
  )
}
