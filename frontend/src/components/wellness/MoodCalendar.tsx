import { motion } from 'framer-motion'

export type MoodPoint = {
    date: string
    mood_score: number
    label: string
    emoji: string | null
}

type Props = {
    points?: MoodPoint[]
    mode?: 'score' | 'completion'
    /** ISO yyyy-mm-dd for completion mode */
    completedDates?: Set<string>
    className?: string
    onDayClick?: (date: string, score: number, label: string) => void
    /** When set with completion mode, opens shared history modal */
    onOpenHistory?: () => void
}

const DAY_LABELS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function scoreAbbrev(score: number): string {
    return `${Math.round(score)}`
}

function scoreToClasses(score: number): string {
    if (score >= 80) return 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/30 dark:border-emerald-800/50 dark:text-emerald-400'
    if (score >= 60) return 'bg-green-50 border-green-200 text-green-700 dark:bg-green-900/30 dark:border-green-800/50 dark:text-green-400'
    if (score >= 40) return 'bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/20 dark:border-amber-800/40 dark:text-amber-400'
    if (score >= 20) return 'bg-orange-50 border-orange-200 text-orange-700 dark:bg-orange-900/20 dark:border-orange-800/40 dark:text-orange-400'
    return 'bg-red-50 border-red-200 text-red-600 dark:bg-red-900/20 dark:border-red-800/40 dark:text-red-400'
}

function buildScoreGrid(points: MoodPoint[]): Array<{ date: string; score: number | null }[]> {
    const today = new Date()
    const dayOfWeek = today.getDay()
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    const startDate = new Date(today)
    startDate.setDate(today.getDate() - daysToMonday - 21)

    const scoreMap = new Map<string, number>()
    for (const p of points) {
        const pct = Math.round((p.mood_score / 5) * 100)
        scoreMap.set(p.date.slice(0, 10), pct)
    }

    const weeks: Array<{ date: string; score: number | null }[]> = []
    for (let week = 0; week < 4; week++) {
        const row: { date: string; score: number | null }[] = []
        for (let day = 0; day < 7; day++) {
            const d = new Date(startDate)
            d.setDate(startDate.getDate() + week * 7 + day)
            const iso = d.toISOString().slice(0, 10)
            const isFuture = d > today
            row.push({ date: iso, score: isFuture ? null : scoreMap.get(iso) ?? null })
        }
        weeks.push(row)
    }
    return weeks
}

function buildCompletionGrid(completedDates: Set<string>): Array<{ date: string; completed: boolean }[]> {
    const today = new Date()
    const dayOfWeek = today.getDay()
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    const startDate = new Date(today)
    startDate.setDate(today.getDate() - daysToMonday - 21)

    const weeks: Array<{ date: string; completed: boolean }[]> = []
    for (let week = 0; week < 4; week++) {
        const row: { date: string; completed: boolean }[] = []
        for (let day = 0; day < 7; day++) {
            const d = new Date(startDate)
            d.setDate(startDate.getDate() + week * 7 + day)
            const iso = d.toISOString().slice(0, 10)
            const isFuture = d > today
            row.push({
                date: iso,
                completed: !isFuture && completedDates.has(iso),
            })
        }
        weeks.push(row)
    }
    return weeks
}

function formatDate(iso: string): string {
    const d = new Date(iso)
    return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function findLabel(points: MoodPoint[], date: string): string {
    const p = points.find((pt) => pt.date.slice(0, 10) === date)
    return p?.label ?? ''
}

export function MoodCalendar({
    points = [],
    mode = 'score',
    completedDates,
    className,
    onDayClick,
    onOpenHistory,
}: Props) {
    const scoreWeeks = mode === 'score' ? buildScoreGrid(points) : []
    const completionWeeks = mode === 'completion' ? buildCompletionGrid(completedDates ?? new Set()) : []

    return (
        <div className={className}>
            <div className="mb-2 grid grid-cols-7 gap-1.5 px-0.5">
                {DAY_LABELS.map((d) => (
                    <div key={d} className="text-center text-[10px] font-semibold uppercase tracking-wider text-theme-text-secondary/60 dark:text-theme-text-tertiary">
                        {d}
                    </div>
                ))}
            </div>

            <div className="space-y-1.5">
                {mode === 'score' &&
                    scoreWeeks.map((week, wi) => (
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
                                                ? () => onDayClick(date, (score! / 100) * 5, findLabel(points, date))
                                                : undefined
                                        }
                                        initial={{ opacity: 0, scale: 0.6 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: idx * 0.012, duration: 0.2, ease: 'backOut' }}
                                        title={score !== null ? `${formatDate(date)}: ${Math.round(score)}%` : formatDate(date)}
                                        className={[
                                            'flex aspect-square items-center justify-center rounded-xl border transition',
                                            isClickable ? 'cursor-pointer hover:scale-110 hover:shadow-sm active:scale-95' : 'cursor-default',
                                            score !== null ? scoreToClasses(score) : 'border-black/10 bg-black/5 dark:border-white/10 dark:bg-white/5',
                                        ].join(' ')}
                                    >
                                        {score !== null ? (
                                            <span className="select-none text-[10px] font-semibold tabular-nums leading-none">
                                                {scoreAbbrev(score)}
                                            </span>
                                        ) : (
                                            <span className="h-1.5 w-1.5 rounded-full bg-serene-outline/25" />
                                        )}
                                    </motion.button>
                                )
                            })}
                        </div>
                    ))}

                {mode === 'completion' &&
                    completionWeeks.map((week, wi) => (
                        <div key={wi} className="grid grid-cols-7 gap-1.5">
                            {week.map(({ date, completed }, di) => {
                                const idx = wi * 7 + di
                                const todayIso = new Date().toISOString().slice(0, 10)
                                const isFuture = date > todayIso
                                const clickable = !isFuture && (!!onOpenHistory || (!!completed && !!onDayClick))
                                return (
                                    <motion.button
                                        key={date}
                                        type="button"
                                        disabled={!clickable}
                                        onClick={() => {
                                            if (onOpenHistory) onOpenHistory()
                                            else if (completed && onDayClick) onDayClick(date, 3, '')
                                        }}
                                        initial={{ opacity: 0, scale: 0.6 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: idx * 0.012, duration: 0.2, ease: 'backOut' }}
                                        title={formatDate(date)}
                                        className={[
                                            'flex aspect-square items-center justify-center rounded-xl border transition',
                                            clickable ? 'cursor-pointer hover:scale-105 active:scale-95' : 'cursor-default',
                                            completed
                                                ? 'border-theme-accent bg-theme-accent text-white shadow-sm'
                                                : isFuture
                                                  ? 'border-transparent bg-transparent'
                                                  : 'border-black/10 bg-black/5 dark:border-white/10 dark:bg-white/5',
                                        ].join(' ')}
                                    >
                                        {completed ? <span className="text-[10px] font-bold">✓</span> : null}
                                    </motion.button>
                                )
                            })}
                        </div>
                    ))}
            </div>
        </div>
    )
}
