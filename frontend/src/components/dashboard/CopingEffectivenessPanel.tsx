import { Sparkles, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReflectInsight } from '../../services/dashboardService'
import { ROUTE_PATHS } from '../../routes/paths'
import PixelEmptyState from '../pixel/PixelEmptyState'

type Props = {
    insights: ReflectInsight[]
}

type CopingEntry = {
    id: string
    label: string
    usedFor: string
    suggestedActionText: string | null
    route: string
    confidenceLabel: string
}

function buildCopingEntries(insights: ReflectInsight[]): CopingEntry[] {
    return insights
        .filter((insight) => insight.suggested_action)
        .slice(0, 3)
        .map((insight) => ({
            id: insight.insight_id,
            label: insight.title,
            usedFor: insight.user_safe_summary.slice(0, 80) + (insight.user_safe_summary.length > 80 ? '…' : ''),
            suggestedActionText: insight.suggested_action ?? null,
            route: ROUTE_PATHS.checkin,
            confidenceLabel: insight.confidence_label,
        }))
}

export function CopingEffectivenessPanel({ insights }: Props) {
    const entries = buildCopingEntries(insights)

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Điều từng giúp</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Điều từng giúp bạn nhẹ hơn</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Sau vài lần thử các bài tập và check-in, Serene sẽ nhận ra việc gì thường giúp bạn ổn hơn.
                </p>
            </div>

            {entries.length === 0 ? (
                <PixelEmptyState
                    mascot="eat"
                    title="Serene chưa biết việc gì giúp bạn ổn hơn."
                    description="Sau vài lần check-in và thử bài tập nhỏ, phần này sẽ rõ hơn và cá nhân hơn."
                    action={
                        <Link
                            to={ROUTE_PATHS.exercises}
                            className="inline-flex items-center gap-2 rounded-full bg-theme-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
                        >
                            Thử một bài tập nhỏ
                            <ArrowRight className="h-4 w-4" aria-hidden />
                        </Link>
                    }
                />
            ) : (
                <div className="space-y-3">
                    {entries.map((entry) => (
                        <div
                            key={entry.id}
                            className="flex flex-col gap-2 rounded-2xl border border-theme-border/60 bg-emerald-50/50 p-4 sm:flex-row sm:items-center sm:justify-between dark:bg-emerald-400/5"
                        >
                            <div className="min-w-0">
                                <div className="mb-1 flex items-center gap-2">
                                    <Sparkles className="h-3.5 w-3.5 shrink-0 text-emerald-500" aria-hidden />
                                    <p className="text-sm font-semibold text-theme-text-primary leading-snug">
                                        {entry.label}
                                    </p>
                                </div>
                                {entry.suggestedActionText && (
                                    <p className="text-xs leading-relaxed text-theme-text-secondary">
                                        {entry.suggestedActionText}
                                    </p>
                                )}
                                <span className="mt-1 inline-block rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-medium text-theme-text-tertiary dark:bg-white/10">
                                    {entry.confidenceLabel}
                                </span>
                            </div>
                            <Link
                                to={entry.route}
                                className="shrink-0 inline-flex items-center gap-1.5 rounded-full border border-emerald-300/70 bg-white/70 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-50 dark:border-emerald-400/30 dark:bg-emerald-400/10 dark:text-emerald-200"
                            >
                                Thử lại
                                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                            </Link>
                        </div>
                    ))}
                </div>
            )}
        </section>
    )
}
