import { Clock3 } from 'lucide-react'
import type { ReflectRecentCheckin } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    checkins: ReflectRecentCheckin[]
    missingData: string[]
}

function formatDate(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-')
    if (!year || !month || !day) return value
    return `${day}/${month}`
}

function compact(values: string[]): string {
    return values.length ? values.slice(0, 2).join(', ') : 'Chưa ghi'
}

export function MoodMiniTimeline({ checkins, missingData }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const moodBadgeClass = isDark
        ? 'bg-cyan-400/15 text-cyan-100'
        : 'bg-cyan-100 text-cyan-800'

    const missingBadgeClass = isDark
        ? 'border-amber-400/20 bg-amber-400/10 text-amber-100'
        : 'border-amber-200 bg-amber-50 text-amber-800'

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                        <Clock3 className="h-4 w-4 text-cyan-500" aria-hidden />
                        Tín hiệu ban đầu
                    </p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Timeline check-in gần đây</h2>
                </div>
                <p className="text-xs text-theme-text-secondary">Dưới 3 check-in nên đọc theo từng bằng chứng, chưa dùng heatmap lớn.</p>
            </div>

            {checkins.length === 0 ? (
                <div className="mt-4 rounded-xl bg-theme-bg-secondary/75 p-4 text-sm text-theme-text-secondary">
                    Chưa có check-in nào trong khoảng này. Hãy tạo check-in đầu tiên để dashboard bắt đầu ghi nhận mood, trigger và cảm xúc.
                </div>
            ) : (
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {checkins.map((checkin) => (
                        <article key={checkin.id} className="rounded-xl border border-theme-border/70 bg-theme-bg-secondary/70 p-3">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-sm font-semibold text-theme-text-primary">{formatDate(checkin.date)}</p>
                                <span className={`rounded-full px-2 py-1 text-xs font-semibold ${moodBadgeClass}`}>
                                    Mood {checkin.mood_score != null ? `${checkin.mood_score}/10` : 'chưa ghi'}
                                </span>
                            </div>
                            <p className="mt-2 text-sm text-theme-text-secondary">Trigger: {compact(checkin.triggers)}</p>
                            <p className="mt-1 text-sm text-theme-text-secondary">Cảm xúc: {compact(checkin.emotions)}</p>
                        </article>
                    ))}
                </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
                {missingData.map((item) => (
                    <span
                        key={item}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${missingBadgeClass}`}
                    >
                        {item}
                    </span>
                ))}
            </div>
        </section>
    )
}
