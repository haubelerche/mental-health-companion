import { ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { ReflectInsight } from '../../services/dashboardService'
import PixelEmptyState from '../pixel/PixelEmptyState'

type Props = {
    insights: ReflectInsight[]
}

const CONFIDENCE_STYLE: Record<string, { badge: string; border: string }> = {
    'Dữ liệu còn ít': {
        badge: 'bg-gray-100 text-gray-600 dark:bg-gray-400/15 dark:text-gray-300',
        border: 'border-gray-200/60',
    },
    'Có vài dấu hiệu': {
        badge: 'bg-amber-50 text-amber-800 dark:bg-amber-400/10 dark:text-amber-200',
        border: 'border-amber-200/60',
    },
    'Khá rõ': {
        badge: 'bg-cyan-50 text-cyan-800 dark:bg-cyan-400/10 dark:text-cyan-200',
        border: 'border-cyan-200/60',
    },
    'Rất nhất quán': {
        badge: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200',
        border: 'border-emerald-200/60',
    },
}

function confidenceStyle(label: string) {
    return CONFIDENCE_STYLE[label] ?? CONFIDENCE_STYLE['Dữ liệu còn ít']
}

function PatternCard({ insight }: { insight: ReflectInsight }) {
    const [expanded, setExpanded] = useState(false)
    const style = confidenceStyle(insight.confidence_label)

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

            <p className="mt-2 text-sm leading-relaxed text-theme-text-secondary">
                {insight.user_safe_summary}
            </p>

            {expanded && (
                <div className="mt-3 space-y-2 border-t border-theme-border/50 pt-3">
                    <div className="flex flex-wrap gap-2 text-xs text-theme-text-secondary">
                        <span className="rounded-full border border-theme-border px-2.5 py-1">
                            {insight.evidence_count} ghi nhận làm cơ sở
                        </span>
                        <span className="rounded-full border border-theme-border px-2.5 py-1">
                            {insight.severity_label}
                        </span>
                    </div>
                    {insight.suggested_action && (
                        <p className="rounded-xl bg-emerald-50/70 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-400/8 dark:text-emerald-200">
                            <span className="font-semibold">Bước tiếp theo: </span>
                            {insight.suggested_action}
                        </p>
                    )}
                </div>
            )}

            <p className="mt-3 text-[11px] text-theme-text-tertiary">
                Đây không phải chẩn đoán. Chỉ là quan sát từ dữ liệu bạn đã ghi lại.
            </p>
        </article>
    )
}

export function PatternGroupCards({ insights }: Props) {
    const visibleInsights = insights.slice(0, 5)

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Dấu hiệu theo dõi</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Dấu hiệu nên theo dõi thêm</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Những quan sát này dựa trên dữ liệu bạn đã ghi lại. Không phải kết luận cố định — chỉ là tín hiệu đáng để chú ý.
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
