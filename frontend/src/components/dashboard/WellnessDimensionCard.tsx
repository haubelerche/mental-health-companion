import { Activity, Heart, Moon, Sprout, TrendingDown, TrendingUp, Users, Wind } from 'lucide-react'
import type { ReflectWellnessDimension, WellnessDimension } from '../../services/dashboardService'

type Props = {
    dimension: ReflectWellnessDimension
}

function statusLabel(status: WellnessDimension['status']): string {
    switch (status) {
        case 'steady':
            return 'Khá ổn'
        case 'improving':
            return 'Đang cải thiện'
        case 'needs_attention':
            return 'Cần chăm thêm'
        case 'limited_data':
            return 'Dữ liệu còn ít'
        default:
            return 'Chưa rõ'
    }
}

function statusClass(status: WellnessDimension['status']): string {
    switch (status) {
        case 'steady':
            return 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-100'
        case 'improving':
            return 'border-cyan-200 bg-cyan-50 text-cyan-800 dark:border-cyan-400/20 dark:bg-cyan-400/10 dark:text-cyan-100'
        case 'needs_attention':
            return 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100'
        default:
            return 'border-neutral-200 bg-neutral-100 text-neutral-700 dark:border-white/10 dark:bg-white/5 dark:text-theme-text-secondary'
    }
}

function DimensionIcon({ dimension }: { dimension: WellnessDimension['dimension'] }) {
    const className = 'h-4 w-4'
    switch (dimension) {
        case 'sleep':
            return <Moon className={className} aria-hidden />
        case 'mindfulness':
            return <Wind className={className} aria-hidden />
        case 'connection':
            return <Users className={className} aria-hidden />
        case 'body':
            return <Activity className={className} aria-hidden />
        case 'growth':
            return <Sprout className={className} aria-hidden />
        case 'emotion':
        default:
            return <Heart className={className} aria-hidden />
    }
}

function TrendCopy({ delta }: { delta?: number | null }) {
    if (typeof delta !== 'number') {
        return <span className="text-theme-text-tertiary">Chưa đủ dữ liệu so sánh</span>
    }
    if (delta > 0) {
        return (
            <span className="inline-flex items-center gap-1 text-cyan-700 dark:text-cyan-200">
                <TrendingUp className="h-3.5 w-3.5" aria-hidden />
                +{delta} so với trước
            </span>
        )
    }
    if (delta < 0) {
        return (
            <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-200">
                <TrendingDown className="h-3.5 w-3.5" aria-hidden />
                {delta} so với trước
            </span>
        )
    }
    return <span className="text-theme-text-secondary">Gần như ổn định</span>
}

export function WellnessDimensionCard({ dimension }: Props) {
    return (
        <article className="min-h-[18rem] rounded-3xl border border-theme-border/70 bg-theme-surface/86 p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md md:p-5">
            <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                    <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-theme-accent-light text-theme-accent">
                        <DimensionIcon dimension={dimension.dimension} />
                    </span>
                    <div className="min-w-0">
                        <h3 className="truncate text-base font-semibold text-theme-text-primary">{dimension.label}</h3>
                        <p className="mt-1 text-xs text-theme-text-secondary">{dimension.evidence_text}</p>
                    </div>
                </div>
                <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusClass(dimension.status)}`}>
                    {statusLabel(dimension.status)}
                </span>
            </div>

            <div className="mt-5 flex items-end justify-between gap-4">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                        Điểm hiện tại
                    </p>
                    <p className="mt-1 text-3xl font-semibold tabular-nums text-theme-text-primary">
                        {dimension.score != null ? `${dimension.score}` : '--'}
                        <span className="text-sm font-medium text-theme-text-tertiary">/100</span>
                    </p>
                </div>
                <p className="pb-1 text-xs font-semibold">
                    <TrendCopy delta={dimension.trend_delta} />
                </p>
            </div>

            <div className="mt-4 h-2 overflow-hidden rounded-full bg-theme-bg-secondary">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400"
                    style={{ width: `${Math.max(0, Math.min(100, dimension.score || 0))}%` }}
                />
            </div>

            <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-theme-text-secondary">{dimension.explanation}</p>
            {dimension.reason && (
                <div className="mt-4 rounded-2xl bg-theme-bg-secondary/70 p-3 text-xs leading-relaxed text-theme-text-secondary">
                    <span className="font-semibold text-theme-text-primary">Điều nên để ý: </span>
                    {dimension.reason}
                </div>
            )}
            {dimension.suggested_action && (
                <p className="mt-3 text-sm leading-relaxed text-theme-accent">
                    <span className="font-semibold">Gợi ý: </span>
                    {dimension.suggested_action}
                </p>
            )}
        </article>
    )
}
