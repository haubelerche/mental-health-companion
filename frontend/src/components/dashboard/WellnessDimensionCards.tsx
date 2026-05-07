import type { WellnessDimension } from '../../services/dashboardService'

type Props = {
    dimensions: WellnessDimension[]
    isDark: boolean
}

function statusStyles(status: WellnessDimension['status']): string {
    switch (status) {
        case 'steady':
            return 'bg-emerald-500/25 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-200'
        case 'improving':
            return 'bg-teal-500/25 text-teal-900 dark:bg-teal-500/15 dark:text-teal-200'
        case 'needs_attention':
            return 'bg-amber-500/25 text-amber-950 dark:bg-amber-500/15 dark:text-amber-100'
        case 'limited_data':
        case 'unknown':
        default:
            return 'bg-neutral-500/20 text-neutral-800 dark:bg-neutral-500/10 dark:text-neutral-300'
    }
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

export function WellnessDimensionCards({ dimensions, isDark }: Props) {
    return (
        <section
            className={`rounded-[1.75rem] border p-4 backdrop-blur-md md:p-6 shadow-sm ${
                isDark ? 'border-theme-border/30 bg-theme-surface/60' : 'border-white/25 bg-white/30'
            }`}
        >
            <p className={`text-[10px] uppercase tracking-[0.3em] ${isDark ? 'text-theme-text-secondary' : 'text-serene-primary/70'}`}>
                6 chiều sức khỏe
            </p>
            <h2 className={`mt-1 font-display text-xl md:text-2xl ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>
                Góc nhìn dễ hiểu từ Serene
            </h2>
            <p className={`mt-2 text-xs md:text-sm ${isDark ? 'text-theme-text-secondary/85' : 'text-serene-muted'}`}>
                Một check-in mỗi ngày là đủ để giữ chuỗi. Nếu muốn, bạn có thể check-in thêm sáng/chiều/tối để Serene hiểu nhịp cảm xúc trong ngày rõ hơn — không bắt buộc.
            </p>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {dimensions.map((d) => (
                    <div
                        key={d.dimension}
                        className={`rounded-2xl border p-4 ${isDark ? 'border-theme-border/25 bg-theme-surface/50' : 'border-theme-border/10 bg-white/70 shadow-sm'}`}
                    >
                        <div className="flex items-start justify-between gap-2">
                            <p className={`font-semibold ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>{d.label}</p>
                            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusStyles(d.status)}`}>
                                {statusLabel(d.status)}
                            </span>
                        </div>
                        <div className="mt-3">
                            {d.score != null ? (
                                <div className="flex items-center gap-2">
                                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
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
