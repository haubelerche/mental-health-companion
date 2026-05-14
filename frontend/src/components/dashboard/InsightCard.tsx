import { CalendarDays, Lightbulb, ShieldCheck } from 'lucide-react'
import type { ReflectInsight } from '../../services/dashboardService'

type Props = {
    insight: ReflectInsight
}

function formatWindow(start: string | null, end: string | null): string {
    if (!start || !end) return 'Khoảng dữ liệu gần đây'
    return `${start.slice(5)}-${end.slice(5)}`
}

function typeLabel(type: string): string {
    return type
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function InsightCard({ insight }: Props) {
    return (
        <article className="rounded-2xl border border-theme-border/70 bg-theme-surface/94 p-4 shadow-sm md:p-5">
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <p className="inline-flex items-center gap-1.5 rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-semibold text-cyan-800 dark:bg-cyan-400/10 dark:text-cyan-100">
                        <Lightbulb className="h-3.5 w-3.5" aria-hidden />
                        {typeLabel(insight.hypothesis_type)}
                    </p>
                    <h3 className="mt-3 text-base font-semibold leading-snug text-theme-text-primary">{insight.title}</h3>
                </div>
                <span className="shrink-0 rounded-full border border-theme-border bg-theme-bg-secondary/70 px-2.5 py-1 text-xs font-semibold text-theme-text-secondary">
                    {insight.confidence_label}
                </span>
            </div>
            <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-theme-text-secondary">{insight.user_safe_summary}</p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-theme-text-secondary">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-theme-border px-3 py-1">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" aria-hidden />
                    Evidence: {insight.evidence_count} ghi nhận
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-theme-border px-3 py-1">
                    <CalendarDays className="h-3.5 w-3.5 text-cyan-500" aria-hidden />
                    {formatWindow(insight.evidence_window_start, insight.evidence_window_end)}
                </span>
                <span className="rounded-full border border-theme-border px-3 py-1">{insight.severity_label}</span>
            </div>
            <div className="mt-4 rounded-xl bg-theme-bg-secondary/70 p-3 text-sm leading-relaxed text-theme-text-secondary">
                <span className="font-semibold text-theme-text-primary">Ý nghĩa: </span>
                Nên đọc như một tín hiệu quan sát trong khoảng đã chọn, không phải kết luận cố định.
            </div>
            {insight.suggested_action && (
                <p className="mt-3 rounded-xl border border-theme-border bg-theme-surface/70 p-3 text-sm leading-relaxed text-theme-text-primary">
                    <span className="font-semibold text-theme-accent">Next: </span>
                    {insight.suggested_action}
                </p>
            )}
        </article>
    )
}
