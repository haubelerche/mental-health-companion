import { Check } from 'lucide-react'

type Props = {
    streak: number
    className?: string
    isTodayCompleted?: boolean
    completedDays?: number[]
}

const DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function getTodayDisplayIndex(): number {
    const day = new Date().getDay() // 0=Sun ... 6=Sat
    return day === 0 ? 6 : day - 1  // map Mon=0 ... Sun=6
}

export function StreakBar({ streak, className, isTodayCompleted = false, completedDays }: Props) {

    const todayIdx = getTodayDisplayIndex()
    const filledCount = Math.min(streak, 7)
    const completedIndices = new Set<number>()
    
    if (completedDays) {
        completedDays.forEach(idx => completedIndices.add(idx))
    } else {
        // Fallback to old logic if completedDays is not provided
        const startIdx = isTodayCompleted ? todayIdx : (todayIdx - 1 + 7) % 7
        for (let offset = 0; offset < filledCount; offset += 1) {
            const idx = (startIdx - offset + 7) % 7
            completedIndices.add(idx)
        }
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
                                'flex h-9 w-9 items-center text-xs justify-center rounded-full font-semibold transition-all',
                                isCompleted
                                    ? ('bg-theme-accent text-white shadow-sm')
                                    : isToday
                                        ? 'text-theme-accent border-3 border-theme-accent'
                                        : ' bg-theme-surface text-theme-text-primary border border-theme-primary/50',
                            ].join(' ')}
                        >
                            {isCompleted ? <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden /> : day}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
