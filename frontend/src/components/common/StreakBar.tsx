import { Check } from 'lucide-react'
import { useThemeContext } from '../../contexts/ThemeContext'
type Props = {
    streak: number
    className?: string
}

const DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function getTodayDisplayIndex(): number {
    const day = new Date().getDay() // 0=Sun ... 6=Sat
    return day === 0 ? 6 : day - 1  // map Mon=0 ... Sun=6
}

export function StreakBar({ streak, className }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'
    const todayIdx = getTodayDisplayIndex()
    const filledCount = Math.min(streak, 7)
    const completedIndices = new Set<number>()
    for (let offset = 0; offset < filledCount; offset += 1) {
        // Mark consecutive streak days backward from today (wrap across week boundary).
        const idx = (todayIdx - offset + 7) % 7
        completedIndices.add(idx)
    }

    return (
        <div className={`flex items-center gap-1.5 ${className ?? ''}`}>
            {DAYS.map((day, idx) => {
                const isCompleted = completedIndices.has(idx)
                const isToday = idx === todayIdx && !isCompleted

                return (
                    <div key={day} className="flex flex-1 flex-col items-center gap-1">
                        <div
                            className={[
                                'flex h-8 w-8 items-center justify-center rounded-full  font-semibold transition-all',
                                isCompleted
                                    ? (isDark ? 'bg-theme-accent text-white shadow-sm' : 'bg-serene-primary text-serene-on-primary shadow-sm')
                                    : isToday
                                        ? (isDark ? 'animate-pulse ring-2 ring-theme-accent ring-offset-1 bg-theme-accent/20 text-theme-accent' : 'animate-pulse ring-2 ring-serene-primary ring-offset-1 bg-serene-accent/30 text-serene-primary')
                                        : `${isDark ? 'border-white/10 bg-white/5 text-white/40' : 'border-white/40 bg-white/50 text-serene-muted'}`,
                            ].join(' ')}
                        >
                            {isCompleted ? <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden /> : day.charAt(0)}
                        </div>
                        <span className={`text-sm ${isDark ? 'text-white/40' : 'text-serene-muted'}`}>{day}</span>
                    </div>
                )
            })}
        </div>
    )
}
