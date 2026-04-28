import { motion } from 'framer-motion'

type MoodPoint = {
    date: string
    mood_score: number
    label: string
    emoji: string | null
}

type Props = {
    points: MoodPoint[]
    className?: string
    onDayClick?: (date: string, score: number, label: string) => void
}

const DAY_LABELS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function scoreToEmoji(score: number): string {
    if (score >= 80) return '😊'
    if (score >= 60) return '😌'
    if (score >= 40) return '😐'
    if (score >= 20) return '😔'
    return '😟'
}

function scoreToClasses(score: number): string {
    if (score >= 80) return 'bg-emerald-50 border-emerald-200 text-emerald-700'
    if (score >= 60) return 'bg-green-50 border-green-200 text-green-700'
    if (score >= 40) return 'bg-amber-50 border-amber-200 text-amber-700'
    if (score >= 20) return 'bg-orange-50 border-orange-200 text-orange-700'
    return 'bg-red-50 border-red-200 text-red-600'
}

function buildGrid(points: MoodPoint[]): Array<{ date: string; score: number | null }[]> {
    const today = new Date()
    const dayOfWeek = today.getDay()
    // Start from Monday 4 weeks ago
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    const startDate = new Date(today)
    startDate.setDate(today.getDate() - daysToMonday - 21)

    const scoreMap = new Map<string, number>()
    for (const p of points) {
        scoreMap.set(p.date.slice(0, 10), p.mood_score)
    }

    const weeks: Array<{ date: string; score: number | null }[]> = []
    for (let week = 0; week < 4; week++) {
        const row: { date: string; score: number | null }[] = []
        for (let day = 0; day < 7; day++) {
            const d = new Date(startDate)
            d.setDate(startDate.getDate() + week * 7 + day)
            const iso = d.toISOString().slice(0, 10)
            const isFuture = d > today
            row.push({ date: iso, score: isFuture ? null : (scoreMap.get(iso) ?? null) })
        }
        weeks.push(row)
    }
    return weeks
}

function formatDate(iso: string): string {
    const d = new Date(iso)
    return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

// Find label for a given date from points array
function findLabel(points: MoodPoint[], date: string): string {
    const p = points.find((pt) => pt.date.slice(0, 10) === date)
    return p?.label ?? ''
}

export function MoodCalendar({ points, className, onDayClick }: Props) {
    const weeks = buildGrid(points)

    return (
        <div className={className}>
            {/* Day-of-week header */}
            <div className="mb-2 grid grid-cols-7 gap-1.5 px-0.5">
                {DAY_LABELS.map((d) => (
                    <div
                        key={d}
                        className="text-center text-[10px] font-semibold uppercase tracking-wider text-serene-muted/55"
                    >
                        {d}
                    </div>
                ))}
            </div>

            {/* Calendar grid */}
            <div className="space-y-1.5">
                {weeks.map((week, wi) => (
                    <div key={wi} className="grid grid-cols-7 gap-1.5">
                        {week.map(({ date, score }, di) => {
                            const idx = wi * 7 + di
                            const isClickable = score !== null && !!onDayClick
                            return (
                                <motion.button
                                    key={date}
                                    type="button"
                                    disabled={!isClickable}
                                    onClick={
                                        isClickable
                                            ? () => onDayClick(date, score!, findLabel(points, date))
                                            : undefined
                                    }
                                    initial={{ opacity: 0, scale: 0.6 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: idx * 0.012, duration: 0.2, ease: 'backOut' }}
                                    title={
                                        score !== null
                                            ? `${formatDate(date)}: ${Math.round(score)}%`
                                            : formatDate(date)
                                    }
                                    className={[
                                        'flex aspect-square items-center justify-center rounded-xl border transition',
                                        isClickable
                                            ? 'cursor-pointer hover:scale-110 hover:shadow-sm active:scale-95'
                                            : 'cursor-default',
                                        score !== null
                                            ? scoreToClasses(score)
                                            : 'border-white/30 bg-white/25',
                                    ].join(' ')}
                                >
                                    {score !== null ? (
                                        <span className="select-none text-[15px] leading-none">
                                            {scoreToEmoji(score)}
                                        </span>
                                    ) : (
                                        <span className="h-1.5 w-1.5 rounded-full bg-serene-outline/25" />
                                    )}
                                </motion.button>
                            )
                        })}
                    </div>
                ))}
            </div>
        </div>
    )
}
