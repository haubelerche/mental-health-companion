import { Play, Clock } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { exerciseService, type ExerciseItem } from '../../../services/exerciseService'
import Loading from '../../ui/Loading'
import { useThemeContext } from '../../../contexts/ThemeContext'
import { ROUTE_PATHS } from '../../../routes/paths'

export function ExerciseTab() {
    const navigate = useNavigate()
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    const [exercises, setExercises] = useState<ExerciseItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        exerciseService.list()
            .then(data => {
                setExercises(data.items)
            })
            .catch(() => setExercises([]))
            .finally(() => setLoading(false))
    }, [])

    if (loading) return <Loading text="Đang tải danh sách bài tập..." />

    if (exercises.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-theme-text-secondary">Chưa có bài tập nào khả dụng.</p>
            </div>
        )
    }

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        return `${mins} phút`
    }

    return (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {exercises.map((ex, idx) => (
                <motion.div
                    key={ex.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`group cursor-pointer relative flex flex-col overflow-hidden rounded-4xl border ${isDark ? 'border-white/10 bg-theme-surface/40' : 'border-white/50 bg-white/60'} p-6 shadow-xl backdrop-blur-xl transition-all hover:-translate-y-1`}
                >
                    <div className="flex-1">
                        <div className="mb-4 flex items-center justify-between">
                            <span className="rounded-full bg-theme-accent/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-theme-accent">
                                {ex.type.replace(/_/g, ' ')}
                            </span>
                            <div className="flex items-center gap-1.5 text-xs text-theme-text-secondary">
                                <Clock className="h-3.5 w-3.5" />
                                {formatDuration(ex.duration_sec)}
                            </div>
                        </div>

                        <h3 className="font-display text-2xl font-semibold text-theme-text-primary">
                            {ex.title}
                        </h3>
                        <p className="mt-2 text-sm leading-relaxed text-theme-text-secondary line-clamp-2">
                            {ex.description}
                        </p>
                    </div>

                    <button
                        onClick={() => navigate(`${ROUTE_PATHS.exercises}?exercise=${ex.id}`)}
                        className={`mt-6 flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-bold uppercase tracking-widest text-white transition-all ${isDark ? 'bg-theme-accent hover:brightness-110' : 'bg-serene-primary hover:brightness-105'} shadow-lg active:scale-95`}
                    >
                        <Play className="h-4 w-4 fill-current" />
                        Bắt đầu ngay
                    </button>
                </motion.div>
            ))}
        </div>
    )
}
