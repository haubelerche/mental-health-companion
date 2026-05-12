import { type LucideIcon } from 'lucide-react'
import { useThemeContext } from '../../../contexts/ThemeContext'

export type ExerciseTabId = 'all' | 'breathing_exercise' | 'grounding_exercise' | 'body_scan'

interface FilterChip {
  id: ExerciseTabId
  label: string
  icon: LucideIcon
}

interface ExerciseFilterChipsProps {
  tabs: FilterChip[]
  activeTab: ExerciseTabId
  onChange: (tab: ExerciseTabId) => void
}

export default function ExerciseFilterChips({ tabs, activeTab, onChange }: ExerciseFilterChipsProps) {
  const { effectiveTheme } = useThemeContext()
  const isDark = effectiveTheme === 'dark'

  return (
    <section aria-labelledby="exercise-filters" className="space-y-4">
      <div>
        <h2 id="exercise-filters" className={`text-sm font-medium uppercase tracking-[0.22em] ${isDark ? 'text-[#F4D28A]' : 'text-[#5F7F68]'}`}>
          Chọn bài
        </h2>
        <p className={`mt-2 text-sm ${isDark ? 'text-[#F4E8C8]/74' : 'text-[#24352D]/72'}`}>
          Ưu tiên những bài ngắn, rõ mục tiêu, dễ bắt đầu ngay khi bạn đang mệt.
        </p>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              aria-pressed={isActive}
              className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5F7F68] focus-visible:ring-offset-2 ${
                isActive
                  ? 'border-[#5F7F68] bg-[#5F7F68] text-white shadow-sm'
                  : isDark
                    ? 'border-white/15 bg-white/5 text-[#F4E8C8] hover:bg-white/10'
                    : 'border-white/35 bg-[#F4E8C8]/55 text-[#24352D] hover:bg-[#F4E8C8]/72'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>
    </section>
  )
}

