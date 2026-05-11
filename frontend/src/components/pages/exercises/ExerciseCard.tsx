import { type LucideIcon } from 'lucide-react'
import { Clock3, Play } from 'lucide-react'
import { motion } from 'framer-motion'

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
}

interface ExerciseCardProps {
  exercise: ExerciseCardData
  onStart: (id: string) => void
  index: number
}

export default function ExerciseCard({ exercise, onStart, index }: ExerciseCardProps) {
  const Icon = exercise.icon

  return (
    <motion.button
      layout
      type="button"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.24, delay: index * 0.03 }}
      onClick={() => onStart(exercise.id)}
      aria-label={`Bắt đầu ${exercise.title}, ${exercise.durationLabel}, ${exercise.recommendedFor}`}
      className="group relative flex h-auto min-h-[300px] flex-col overflow-hidden rounded-[24px] border border-white/35 bg-[#F8F1DC]/95 p-6 text-left shadow-[0_16px_36px_rgba(16,35,31,0.10)] backdrop-blur-sm transition-transform duration-200 ease-out hover:-translate-y-1 hover:bg-[#F8F1DC]/98 motion-reduce:transform-none motion-reduce:transition-none motion-reduce:hover:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 dark:border-white/15 dark:bg-[#10231F]/90 dark:hover:bg-[#10231F]/95"
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${exercise.gradient} opacity-60 rounded-[24px] pointer-events-none`} aria-hidden />
      <div className="relative flex h-full flex-col">
        <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/50 bg-white/40 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.25em] text-[#2d4a3f] dark:border-white/20 dark:bg-white/10 dark:text-[#E8DCC8] flex-shrink-0 whitespace-nowrap shadow-sm">
            <Icon className="h-4 w-4 flex-shrink-0" />
            {exercise.tone}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/50 bg-white/40 px-3 py-1.5 text-[11px] font-bold text-[#2d4a3f] dark:border-white/20 dark:bg-white/10 dark:text-[#E8DCC8] flex-shrink-0 whitespace-nowrap shadow-sm">
            <Clock3 className="h-4 w-4 flex-shrink-0" />
            {exercise.durationLabel}
          </span>
        </div>

        <h3 className="mt-3 text-lg font-bold tracking-tight text-[#1a2623] dark:text-[#F4E8C8] line-clamp-2 leading-tight">
          {exercise.title}
        </h3>
        <p className="mt-3 text-sm leading-5 text-[#2d4a3f] dark:text-[#E8DCC8]/90 line-clamp-3 font-medium">
          {exercise.description}
        </p>

        <div className="mt-auto space-y-4 pt-5">
          <div>
            <p className="text-[11px] uppercase tracking-[0.25em] font-bold text-[#5F7F68] dark:text-[#D4AF7A]">
              Cấu trúc
            </p>
            <p className="mt-2 text-base font-bold text-[#1a2623] dark:text-[#F4E8C8]">
              {exercise.structure}
            </p>
          </div>

          <div className="flex items-end justify-between gap-3">
            <p className="flex-1 text-sm leading-5 text-[#2d4a3f] dark:text-[#E8DCC8]/85 line-clamp-2 font-medium">
              {exercise.recommendedFor}
            </p>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#5F7F68] text-white transition-transform duration-200 ease-out group-hover:translate-x-0.5 group-hover:scale-110 flex-shrink-0 shadow-md">
              <Play className="h-5 w-5 fill-current" />
            </div>
          </div>
        </div>
      </div>
    </motion.button>
  )
}
