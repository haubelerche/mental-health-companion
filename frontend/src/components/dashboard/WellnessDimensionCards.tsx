import { Activity, Heart, Moon, Sprout, Users, Wind } from 'lucide-react'
import type { WellnessDimension } from '../../services/dashboardService'

type Props = {
    dimensions: WellnessDimension[]
    isDark: boolean
}



function statusLabel(status: WellnessDimension['status']): string {
    switch (status) {
        case 'steady':
            return 'Khá ổn'
        case 'improving':
            return 'Đang cải thiện nhẹ'
        case 'needs_attention':
            return 'Cần chút chăm sóc'
        case 'limited_data':
            return 'Dữ liệu còn ít'
        default:
            return 'Chưa rõ'
    }
}

function DimensionIcon({ dimension }: { dimension: WellnessDimension['dimension'] }) {
    const iconClass = 'h-4 w-4'
    switch (dimension) {
        case 'sleep':
            return <Moon className={iconClass} aria-hidden />
        case 'mindfulness':
            return <Wind className={iconClass} aria-hidden />
        case 'connection':
            return <Users className={iconClass} aria-hidden />
        case 'body':
            return <Activity className={iconClass} aria-hidden />
        case 'growth':
            return <Sprout className={iconClass} aria-hidden />
        case 'emotion':
        default:
            return <Heart className={iconClass} aria-hidden />
    }
}

export function WellnessDimensionCards({ dimensions, isDark }: Props) {
    function statusStyles(status: WellnessDimension['status']): string {
   switch (status) {
    case 'steady':
        return isDark
            ? 'bg-emerald-500/15 text-emerald-200 border border-emerald-400/20'
            : 'bg-emerald-100 text-emerald-800 border border-emerald-200'

    case 'improving':
        return isDark
            ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-400/20'
            : 'bg-cyan-100 text-cyan-800 border border-cyan-200'

    case 'needs_attention':
        return isDark
            ? 'bg-amber-500/15 text-amber-100 border border-amber-400/20'
            : 'bg-amber-100 text-amber-900 border border-amber-200'

    case 'limited_data':
    case 'unknown':
    default:
        return isDark
            ? 'bg-white/8 text-neutral-300 border border-white/10'
            : 'bg-neutral-100 text-neutral-700 border border-neutral-200'
    }
}
    return (
        <section
            className={`rounded-[1.75rem] p-4  md:p-8 `}
        >
            <p className={`text-sm font-bold uppercase tracking-[0.3em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary'}`}>
                6 chiều sức khỏe
            </p>
           
            <p className={`mt-2 text-xs md:text-sm ${isDark ? 'text-theme-text-secondary/85' : 'text-serene-muted'}`}>
                Một check-in mỗi ngày là đủ để giữ chuỗi. Nếu muốn, bạn có thể check-in thêm sáng/chiều/tối để Serene hiểu nhịp cảm xúc trong ngày rõ hơn — không bắt buộc.
            </p>
            <p className={`mt-1 text-[10px] uppercase tracking-[0.2em] ${isDark ? 'text-theme-text-secondary/60' : 'text-serene-muted/80'}`}>
                Vuốt ngang để xem đủ 6 chiều
            </p>

            <div
                className="mt-4 -mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto overflow-y-visible overscroll-x-contain px-1 pb-2 pt-1 scroll-px-4 [scrollbar-gutter:stable]"
                style={{ WebkitOverflowScrolling: 'touch' }}
            >
                {dimensions.map((d) => (
                    <div
                        key={d.dimension}
                        className={`w-[min(20rem,calc(100vw-2.5rem))] shrink-0 snap-start rounded-2xl border p-4 sm:w-80 border-theme-secondary/50 bg-theme-surface`}
                    >
                        <div className="flex items-start justify-between gap-2">
                            <p className={`flex min-w-0 items-center gap-2 font-semibold ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>
                                <span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${isDark ? 'bg-theme-accent/15 text-theme-accent' : 'bg-primary/10 text-primary'}`}>
                                    <DimensionIcon dimension={d.dimension} />
                                </span>
                                <span className="min-w-0 truncate">{d.label}</span>
                            </p>
                            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusStyles(d.status)}`}>
                                {statusLabel(d.status)}
                            </span>
                        </div>
                        <div className="mt-3">
                            {d.score != null ? (
                                <div className="flex items-center gap-2">
                                    <div className={`h-2 flex-1 overflow-hidden rounded-full ${isDark ? 'bg-white/10' : 'bg-black/10'}`}>
                                        <div
                                            className="h-full rounded-full bg-theme-accent"
                                            style={{ width: `${Math.min(100, Math.max(0, d.score))}%` }}
                                        />
                                    </div>
                                    <span className="text-xs font-semibold tabular-nums text-theme-text-primary">{d.score}</span>
                                </div>
                            ) : (
                                <p className="text-sm font-medium text-theme-text-secondary">—</p>
                            )}
                        </div>
                        <p className={`mt-3 text-xs leading-relaxed md:text-[13px] ${isDark ? 'text-theme-text-secondary' : 'text-serene-ink/85'}`}>
                            {d.explanation}
                        </p>
                        <p className={`mt-2 text-[10px] uppercase tracking-wide ${isDark ? 'text-theme-text-secondary/70' : 'text-serene-muted'}`}>
                            {d.evidence_count > 0 ? `${d.evidence_count} ghi nhận liên quan` : 'Chưa có ghi nhận đủ'}
                        </p>
                        {d.suggested_action && (
                            <p className={`mt-2 text-xs italic ${isDark ? 'text-theme-accent/90' : 'text-theme-accent'}`}>
                                Gợi ý nhỏ: {d.suggested_action}
                            </p>
                        )}
                    </div>
                ))}
            </div>
        </section>
    )
}
