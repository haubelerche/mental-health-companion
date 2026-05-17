import { ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { ReflectInsight } from '../../services/dashboardService'
import PixelEmptyState from '../pixel/PixelEmptyState'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    insights: ReflectInsight[]
}

function PatternCard({ insight }: { insight: ReflectInsight }) {
    const [expanded, setExpanded] = useState(false)
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const CONFIDENCE_STYLE: Record<string, { badge: string; border: string }> = {
        'Dữ liệu còn ít': {
            badge: isDark ? 'bg-gray-400/15 text-gray-300' : 'bg-gray-100 text-gray-600',
            border: 'border-gray-200/60',
        },
        'Dữ liệu mức vừa': {
            badge: isDark ? 'bg-amber-400/10 text-amber-200' : 'bg-amber-50 text-amber-800',
            border: 'border-amber-200/60',
        },
        'Khá rõ': {
            badge: isDark ? 'bg-cyan-400/10 text-cyan-200' : 'bg-cyan-50 text-cyan-800',
            border: 'border-cyan-200/60',
        },
        'Rất nhất quán': {
            badge: isDark ? 'bg-emerald-400/10 text-emerald-200' : 'bg-emerald-50 text-emerald-800',
            border: 'border-emerald-200/60',
        },
    }

    const style = CONFIDENCE_STYLE[insight.confidence_label] ?? CONFIDENCE_STYLE['Dữ liệu còn ít']

    const suggestedActionClass = isDark
        ? 'bg-emerald-400/8 text-emerald-200'
        : 'bg-emerald-50/70 text-emerald-800'
    const nextAction = insight.recommended_actions?.[0] || insight.suggested_action

    return (
        <article className={`rounded-2xl border ${style.border} bg-theme-surface/94 p-4 shadow-sm`}>
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${style.badge}`}>
                        <ShieldCheck className="h-3 w-3" aria-hidden />
                        {insight.confidence_label}
                    </span>
                    <h3 className="mt-2 text-base font-semibold leading-snug text-theme-text-primary">
                        {insight.title}
                    </h3>
                </div>
                <button
                    type="button"
                    onClick={() => setExpanded(!expanded)}
                    className="mt-1 shrink-0 rounded-full p-1.5 text-theme-text-tertiary hover:bg-theme-bg-secondary/60"
                    aria-expanded={expanded}
                    aria-label={expanded ? 'Thu gọn' : 'Xem thêm'}
                >
                    {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
            </div>

            <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.14em] text-theme-text-tertiary">
                Serene nhận thấy gì
            </p>
            <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                {insight.user_safe_summary}
            </p>
            {insight.interpretation && insight.interpretation !== insight.user_safe_summary && (
                <>
                    <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.14em] text-theme-text-tertiary">
                        Điều này có thể có nghĩa là gì
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-theme-text-primary">
                        {insight.interpretation}
                    </p>
                </>
            )}

            {nextAction && (
                <p className={`mt-3 rounded-xl px-3 py-2 text-sm ${suggestedActionClass}`}>
                    <span className="font-semibold">Bước tiếp theo: </span>
                    {nextAction}
                </p>
            )}

            {expanded && (
                <div className="mt-3 space-y-2 border-t border-theme-border/50 pt-3">
                    <div className="flex flex-wrap gap-2 text-xs text-theme-text-secondary">
                        <span className="rounded-full border border-theme-border px-2.5 py-1">
                            Dựa trên dữ liệu nào: {insight.evidence_count} ghi nhận
                        </span>
                        <span className="rounded-full border border-theme-border px-2.5 py-1">
                            {insight.severity_label}
                        </span>
                    </div>
                    {!!insight.missing_data?.length && (
                        <p className="text-xs leading-relaxed text-theme-text-tertiary">
                            Còn thiếu: {insight.missing_data.slice(0, 2).join(' ')}
                        </p>
                    )}
                </div>
            )}

           
        </article>
    )
}

export function PatternGroupCards({ insights }: Props) {
    const priority = new Map([
        ['weekly_life_state', 0],
        ['daily_mood', 1],
        ['trigger_impact', 2],
        ['sleep', 3],
        ['nutrition', 4],
        ['real_world_connection', 5],
        ['self_care_action', 6],
        ['screening', 7],
    ])
    const visibleInsights = [...insights]
        .sort((a, b) => (priority.get(a.category || a.hypothesis_type) ?? 20) - (priority.get(b.category || b.hypothesis_type) ?? 20))
        .slice(0, 6)

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-4">
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Serene nhận thấy gì</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Những quan sát này dựa trên dữ liệu bạn đã ghi lại.
                </p>
            </div>

            {visibleInsights.length === 0 ? (
                <PixelEmptyState
                    mascot="rock"
                    title="Chưa có dấu hiệu nổi bật."
                    description="Serene cần thêm vài lần check-in để nhận ra pattern. Ghi nhận đều hơn sẽ giúp phần này rõ hơn."
                />
            ) : (
                <div className="space-y-3">
                    {visibleInsights.map((insight) => (
                        <PatternCard key={insight.insight_id} insight={insight} />
                    ))}
                </div>
            )}
        </section>
    )
}
