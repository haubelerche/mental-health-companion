import { type LucideIcon } from 'lucide-react'


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


  return (
    <section aria-labelledby="exercise-filters" className="py-6!">
      <div className="flex flex-wrap gap-3">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              aria-pressed={isActive}
              className={`pixel-btn inline-flex shrink-0 items-center gap-2 px-3! py-0.5! text-xs transition-all active:scale-95 ${
                isActive
                  ? ''
                  : 'pixel-btn-outline'
              }`}
              style={{ 
                borderRadius: '4px',
                ...(isActive ? {} : { background: 'var(--bg-deep)', color: 'var(--text-primary)', borderColor: 'var(--text-primary)' })
              }}
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
