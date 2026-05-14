import { type LucideIcon } from 'lucide-react'
import { Clock3, Play } from 'lucide-react'
import { motion } from 'framer-motion'
import { useThemeContext } from '../../../contexts/ThemeContext'

export interface ExerciseCardData {
  id: string
  type: 'breathing_exercise' | 'grounding_exercise' | 'body_scan'
  title: string
  durationLabel: string
  description: string
  structure: string
  recommendedFor: string
  tone: string
  gradient: string
  icon: LucideIcon
  audioSrc?: string
}

interface ExerciseCardProps {
  exercise: ExerciseCardData
  onStart: (id: string) => void
  index: number
}

export default function ExerciseCard({ exercise, onStart, index }: ExerciseCardProps) {
  const Icon = exercise.icon
  const { effectiveTheme } = useThemeContext()
  const isDark = effectiveTheme === 'dark'

  return (
    <motion.button
      layout
      type="button"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      onClick={() => onStart(exercise.id)}
      aria-label={`Bắt đầu ${exercise.title}, ${exercise.durationLabel}, ${exercise.recommendedFor}`}
      className={`pixel-card group relative flex h-auto min-h-[280px] flex-col overflow-hidden p-7 text-left transition-all duration-300 hover:translate-x-[-2px] hover:translate-y-[-2px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2`}
      style={{
        borderColor: exercise.gradient,
        borderWidth: '2px',
        borderRadius: '4px',
      }}
    >
      <div className="relative flex h-full flex-col gap-3">
        <div className="flex items-start justify-between">
          <div 
            className="flex h-12 w-12 items-center justify-center border-2 bg-theme-bg-secondary" 
            style={{ borderColor: exercise.gradient, color: exercise.gradient }}
          >
            <Icon className="h-6 w-6" />
          </div>
          <span 
            className="pixel-label inline-flex items-center gap-1 px-2 py-1 text-[12px] font-bold"
            style={{ color: exercise.gradient }}
          >
            <Clock3 className="h-3 w-3" />
            {exercise.durationLabel}
          </span>
        </div>

        <div className="mt-2">
          <p className="pixel-label text-[12px] font-bold opacity-80" style={{ color: exercise.gradient }}>
            {exercise.tone}
          </p>
          <h3 className="pixel-headline-sm mt-1 text-2xl font-bold tracking-tight" style={{ color: exercise.gradient, fontSize: '1.8rem' }}>
            {exercise.title}
          </h3>
          <p className="vn-body mt-2 text-sm leading-relaxed line-clamp-2 font-medium">
            {exercise.description}
          </p>
        </div>

        <div className="mt-auto pt-6 flex items-end justify-between">
          <div className="flex flex-col gap-1">
            <p className="pixel-label text-[10px] font-bold opacity-50">
              Cấu trúc
            </p>
            <p className="vn-body text-sm font-bold opacity-90">
              {exercise.structure}
            </p>
          </div>
          
          <div 
            className="flex h-10 w-10 items-center justify-center border-2 transition-all duration-300 group-hover:scale-110 bg-theme-bg-secondary"
            style={{ borderColor: exercise.gradient, color: exercise.gradient }}
          >
            <Play className="h-4 w-4 fill-current ml-0.5" />
          </div>
        </div>
      </div>
    </motion.button>
  )
}

