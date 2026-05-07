import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Pause, Play, Waves, X, Wind, Focus, Accessibility, LayoutGrid, Clock } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ocean from '../../assets/bg-reflect.png'
import { ROUTE_PATHS } from '../../routes/paths'
import { exerciseService, FALLBACK_EXERCISES, findFallbackExercise, type ExerciseItem } from '../../services/exerciseService'
import { useThemeContext } from '../../contexts/ThemeContext'
import Loading from '../ui/Loading'

type TabType = 'all' | 'breathing_exercise' | 'grounding_exercise' | 'body_scan'

const TABS: { id: TabType; label: string; icon: any }[] = [
    { id: 'all', label: 'Tất cả', icon: LayoutGrid },
    { id: 'breathing_exercise', label: 'Hít thở', icon: Wind },
    { id: 'grounding_exercise', label: 'Tâm thức', icon: Focus },
    { id: 'body_scan', label: 'Quét cơ thể', icon: Accessibility },
]

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
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const [exercises, setExercises] = useState<ExerciseItem[]>(FALLBACK_EXERCISES)
    const [selectedId, setSelectedId] = useState(FALLBACK_EXERCISES[0].id)
    const [elapsed, setElapsed] = useState(0)
    const [isRunning, setIsRunning] = useState(false)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<TabType>('all')

    useEffect(() => {
        exerciseService.list()
            .then((data) => {
                if (data.items.length) setExercises(data.items)
            })
            .catch(() => undefined)
            .finally(() => setLoading(false))
    }, [])

    const selectedFromQuery = searchParams.get('exercise')
    const isHubMode = !selectedFromQuery
    const activeId = searchParams.get('exercise') || selectedId
    const exercise = exercises.find((item) => item.id === activeId) ?? findFallbackExercise(activeId)
    const remaining = Math.max(0, exercise.duration_sec - elapsed)
    const progress = Math.min(100, Math.round((elapsed / exercise.duration_sec) * 100))
    const phase = useMemo(() => getBreathPhase(exercise, elapsed), [exercise, elapsed])
    const isDone = elapsed >= exercise.duration_sec

    const filteredExercises = useMemo(() => {
        if (activeTab === 'all') return exercises
        return exercises.filter(ex => ex.type === activeTab)
    }, [exercises, activeTab])

    const getPatternLabel = (item: ExerciseItem) => {
        if (!item.pattern) return 'Nhịp tự do'
        const parts = [item.pattern.inhale, item.pattern.hold, item.pattern.exhale]
        if (item.pattern.hold2 && item.pattern.hold2 > 0) parts.push(item.pattern.hold2)
        return parts.join('-')
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

    if (loading) return <Loading text="Đang chuẩn bị không gian tĩnh lặng..." />

    return (
        <div className={`relative min-h-screen overflow-hidden text-theme-text-primary`}>
            {/* Background Layer */}
            <div className="fixed inset-0 z-0">
                <img src={ocean} alt="Background" className="h-full w-full object-cover" />
                <div className={`absolute inset-0 ${isDark ? 'brightness-60 ' : 'brightness-80'} backdrop-blur-[2px]`} />
            </div>

            <div className="relative z-10 mx-auto max-w-6xl px-4 py-8 md:px-8">
                {isHubMode ? (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-8"
                    >
                        {/* Header Section */}
                        <div className="flex items-center justify-between bg-theme-surface/80 backdrop-blur-xl rounded-4xl p-4">
                            <div>
                                <h1 className="font-display text-4xl font-semibold tracking-tight md:text-5xl">
                                    Hành trình tâm thức
                                </h1>
                                <p className="mt-2 text-theme-text-secondary/80">
                                    Chọn một bài tập để bắt đầu kết nối với chính mình
                                </p>
                            </div>
                            <button
                                onClick={() => navigate(ROUTE_PATHS.resources)}
                                className={`group flex h-12 w-12 items-center justify-center rounded-full border border-theme-border bg-theme-surface/50 backdrop-blur-md transition-all hover:bg-theme-surface`}
                            >
                                <X className="h-5 w-5 transition-transform group-hover:rotate-90" />
                            </button>
                        </div>

                        {/* Tabs Navigation */}
                        <div className="flex flex-wrap gap-2 md:gap-3">
                            {TABS.map((tab) => {
                                const Icon = tab.icon
                                const isActive = activeTab === tab.id
                                return (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={`flex items-center gap-2.5 rounded-2xl px-5 py-3 text-sm font-medium transition-all duration-300 ${isActive
                                                ? 'bg-theme-accent text-white shadow-lg shadow-theme-accent/20 scale-105'
                                                : 'bg-theme-surface border border-theme-border/50 hover:bg-theme-surface/60'
                                            }`}
                                    >
                                        <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-theme-accent'}`} />
                                        {tab.label}
                                    </button>
                                )
                            })}
                        </div>

                        {/* Exercises Grid */}
                        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                            <AnimatePresence mode="popLayout">
                                {filteredExercises.map((item, idx) => (
                                    <motion.button
                                        layout
                                        key={item.id}
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        transition={{ duration: 0.2, delay: idx * 0.05 }}
                                        onClick={() => startExercise(item.id)}
                                        className={`group relative flex flex-col overflow-hidden rounded-[2.5rem] border border-theme-border bg-theme-surface/80 p-7 text-left shadow-xl backdrop-blur-xl transition-all hover:-translate-y-1.5 hover:bg-theme-surface/80`}
                                    >
                                        <div className="flex-1">
                                            <div className="flex items-center justify-between">
                                                <span className="rounded-full bg-theme-accent/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-theme-accent">
                                                    {item.type.replace(/_/g, ' ')}
                                                </span>
                                                <div className="flex items-center gap-1.5 text-xs text-theme-text-secondary">
                                                    <Clock className="h-3.5 w-3.5" />
                                                    {Math.round(item.duration_sec / 60)} phút
                                                </div>
                                            </div>

                                            <h3 className="mt-5 font-display text-3xl font-semibold leading-tight">
                                                {item.title}
                                            </h3>
                                            <p className="mt-2 text-sm leading-relaxed text-theme-text-secondary/80 line-clamp-2">
                                                {item.description}
                                            </p>
                                        </div>

                                        <div className="mt-8 flex items-center justify-between">
                                            <div className="flex flex-col">
                                                <span className="text-[10px] uppercase tracking-widest text-theme-text-secondary/60">Cấu trúc</span>
                                                <span className="text-xl font-semibold text-theme-accent">{getPatternLabel(item)}</span>
                                            </div>
                                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-theme-accent text-white opacity-0 transition-all group-hover:opacity-100">
                                                <Play className="h-5 w-5 fill-current" />
                                            </div>
                                        </div>
                                    </motion.button>
                                ))}
                            </AnimatePresence>
                        </div>

                        {/* Featured Tip Section */}
                        <div className={`mt-8 overflow-hidden rounded-[3rem] border border-theme-border bg-theme-surface/70 p-8 backdrop-blur-xl`}>
                            <div className="flex flex-col gap-6 md:flex-row md:items-center">
                                <div className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-3xl bg-theme-accent/10 text-4xl`}>
                                    🌬️
                                </div>
                                <div className="space-y-2">
                                    <h3 className="font-display text-2xl font-semibold">Lời khuyên nhỏ</h3>
                                    <p className="max-w-2xl text-theme-text-secondary/80">
                                        Hãy tìm một không gian yên tĩnh, ngồi hoặc nằm thoải mái. Đừng quá ép buộc bản thân, hãy để hơi thở trôi chảy tự nhiên nhất có thể.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className={`flex min-h-[80vh] flex-col rounded-[3rem] border border-theme-border bg-theme-surface/70 p-6 shadow-2xl backdrop-blur-2xl md:p-10`}
                    >
                        {/* Player Header */}
                        <header className="flex items-center justify-between">
                            <button
                                onClick={backToHub}
                                className={`flex h-12 w-12 items-center justify-center rounded-full border border-theme-border bg-theme-surface/50 transition-all hover:bg-theme-surface`}
                            >
                                <X className="h-5 w-5" />
                            </button>
                            <div className="text-center">
                                <p className="font-display text-2xl font-semibold md:text-3xl">{exercise.title}</p>
                                <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60 mt-1">{exercise.type.replace(/_/g, ' ')}</p>
                            </div>
                            <button
                                onClick={resetExercise}
                                className={`rounded-full border border-theme-border px-5 py-2 text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary transition-all hover:bg-theme-surface`}
                            >
                                Reset
                            </button>
                        </header>

                        {/* Player Main Area */}
                        <main className="flex flex-1 flex-col items-center justify-center py-12 text-center">
                            <div className="relative mb-12 flex items-center justify-center">
                                {/* Animated Rings */}
                                <motion.div
                                    animate={{ 
                                        scale: isRunning ? phase.scale * 1.1 : 1,
                                        opacity: isRunning ? [0.2, 0.4, 0.2] : 0.2
                                    }}
                                    transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                                    className="absolute h-80 w-80 rounded-full border-2 border-theme-accent/30"
                                />
                                <motion.div
                                    animate={{ 
                                        scale: isRunning ? phase.scale * 1.3 : 1,
                                        opacity: isRunning ? [0.1, 0.2, 0.1] : 0.1
                                    }}
                                    transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                                    className="absolute h-96 w-96 rounded-full border-2 border-theme-accent/20"
                                />

                                <motion.div
                                    animate={{ scale: isRunning ? phase.scale : 1 }}
                                    transition={{ duration: 1.1, ease: 'easeInOut' }}
                                    className={`relative flex h-64 w-64 items-center justify-center rounded-full bg-theme-surface/40 shadow-2xl backdrop-blur-md md:h-80 md:w-80`}
                                >
                                    <div className={`relative flex h-32 w-32 items-center justify-center rounded-full bg-theme-accent text-white shadow-xl`}>
                                        <Waves className="h-10 w-10" />
                                    </div>
                                </motion.div>
                            </div>

                            <div className="space-y-4">
                                <motion.p 
                                    key={phase.label}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`font-display text-4xl font-semibold tracking-wide`}
                                >
                                    {isDone ? 'Phiên tập kết thúc' : phase.label}
                                </motion.p>
                                <p className="text-5xl font-light text-theme-accent tabular-nums">
                                    {isDone ? '✨' : phase.count}
                                </p>
                            </div>

                            {/* Progress Bar */}
                            <div className="mt-12 w-full max-w-md space-y-3">
                                <div className={`h-2 overflow-hidden rounded-full bg-theme-border/30`}>
                                    <motion.div 
                                        className={`h-full rounded-full bg-theme-accent`}
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                                <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60">
                                    <span>Đã qua: {formatTime(elapsed)}</span>
                                    <span>Còn lại: {formatTime(remaining)}</span>
                                </div>
                            </div>

                            {/* Control Button */}
                            <motion.button
                                onClick={() => (isDone ? resetExercise() : setIsRunning(!isRunning))}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                className={`mt-12 flex h-24 w-24 items-center justify-center rounded-full ${isRunning ? 'bg-theme-surface border border-theme-border text-theme-accent' : 'bg-theme-accent text-white'} shadow-2xl transition-all`}
                            >
                                {isRunning ? <Pause className="h-10 w-10 fill-current" /> : <Play className="ml-1 h-10 w-10 fill-current" />}
                            </motion.button>
                        </main>

                        {/* Pattern Overview */}
                        <div className="mt-auto grid grid-cols-3 gap-4 border-t border-theme-border/30 pt-8">
                            {exercise.pattern ? (
                                <>
                                    <div className="text-center">
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60">Hít vào</p>
                                        <p className="mt-1 font-display text-2xl">{exercise.pattern.inhale}s</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60">Giữ</p>
                                        <p className="mt-1 font-display text-2xl">{exercise.pattern.hold}s</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60">Thở ra</p>
                                        <p className="mt-1 font-display text-2xl">{exercise.pattern.exhale}s</p>
                                    </div>
                                </>
                            ) : (
                                <div className="col-span-3 text-center px-4">
                                    <p className="text-sm italic text-theme-text-secondary/80">"{exercise.description}"</p>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    )
}
