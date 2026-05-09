import { Link } from 'react-router-dom'
import type { DashboardSufficiency, InsightCard } from '../../services/dashboardService'
import { ROUTE_PATHS } from '../../routes/paths'

type Props = {
    sufficiency: DashboardSufficiency
    insights: InsightCard[]
    isDark: boolean
}

function confidenceLabel(c: InsightCard['confidence']): string {
    if (c === 'high') return 'Xu hướng khá rõ'
    if (c === 'medium') return 'Độ rõ vừa phải'
    return 'Dữ liệu còn ít'
}

function titleForLevel(level: DashboardSufficiency['readiness_level']): string {
    switch (level) {
        case 'no_data':
            return 'Chưa đủ dữ liệu'
        case 'first_signals':
            return 'Đã có tín hiệu đầu tiên'
        case 'early_insight':
            return 'Tín hiệu ban đầu'
        case 'weekly_trend':
            return 'Xu hướng tuần'
        case 'stable_pattern':
            return 'Xu hướng ổn định hơn'
        default:
            return 'Tín hiệu tuần này'
    }
}

export function SignCard({ sufficiency, insights, isDark }: Props) {
    const level = sufficiency.readiness_level
    const primary = insights[0]
    const bodyText =
        level === 'no_data'
            ? 'Serene cần thêm vài check-in hoặc một vài phiên trò chuyện để nhận ra xu hướng đáng tin hơn.'
            : sufficiency.message

    const chips: string[] = []
    if (sufficiency.mood_checkin_count > 0) {
        chips.push(`${sufficiency.mood_checkin_count} check-in`)
    }
    if (sufficiency.total_session_count > 0) {
        chips.push(`${sufficiency.total_session_count} phiên trò chuyện`)
    }
    if (sufficiency.calendar_days_observed > 0) {
        chips.push(`${sufficiency.calendar_days_observed} ngày gần đây`)
    }

    return (
        <section
            className={`rounded-[1.75rem] border p-4 backdrop-blur-md md:p-6 shadow-sm border-theme-secondary/10 bg-theme-surface/40`}
        >
            <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className={`mt-1 font-display text-xl md:text-2xl ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>
                        {titleForLevel(level)}
                    </h2>
                </div>
                {primary && level !== 'no_data' && level !== 'first_signals' && (
                    <span
                        className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide bg-theme-accent/50 text-theme-on-accent`}
                    >
                        {confidenceLabel(primary.confidence)}
                    </span>
                )}
            </div>

            <p className={`text-sm leading-relaxed md:text-base ${isDark ? 'text-theme-text-secondary' : 'text-serene-ink/85'}`}>
                {bodyText}
            </p>

            {(level === 'no_data' || level === 'first_signals') && sufficiency.next_data_needed.length > 0 && (
                <ul className={`mt-3 list-disc space-y-1 pl-5 text-xs md:text-sm ${isDark ? 'text-theme-text-secondary/90' : 'text-serene-muted'}`}>
                    {sufficiency.next_data_needed.map((line) => (
                        <li key={line}>{line}</li>
                    ))}
                </ul>
            )}

            {chips.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                    {chips.map((c) => (
                        <span
                            key={c}
                            className={`rounded-full px-3 py-1 text-[11px] font-medium text-theme-text-primary border border-theme-secondary/50`}
                        >
                            {c}
                        </span>
                    ))}
                </div>
            )}

            {(level === 'early_insight' || level === 'weekly_trend' || level === 'stable_pattern') && primary && (
                <div
                    className={`mt-4 rounded-2xl border p-4 border-theme-secondary/50 shadow-xl bg-theme-surface/50`}
                >
                    <p className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-theme-accent' : 'text-primary'}`}>
                        {primary.title}
                    </p>
                    <p className={`mt-2 text-sm leading-relaxed md:text-[15px] text-theme-text-primary`}>
                        {primary.user_safe_summary}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-theme-text-secondary">
                        <span>Dựa trên {primary.evidence_count} ghi nhận</span>
                        {(level === 'weekly_trend' || level === 'stable_pattern') &&
                            sufficiency.evidence_window_start &&
                            sufficiency.evidence_window_end && (
                                <span className="rounded-full bg-black/5 px-2 py-0.5 dark:bg-white/10">
                                    {sufficiency.evidence_window_start} - {sufficiency.evidence_window_end}
                                </span>
                            )}
                        {primary.evidence_sources.slice(0, 2).map((s) => (
                            <span key={s} className="rounded-full bg-theme-accent/15 text-theme-on-accent px-2 py-0.5">
                                {s}
                            </span>
                        ))}
                    </div>
                    {primary.suggested_action && (
                        <p className={`mt-3 text-sm italic text-theme-accent`}>
                            <span className='underline '>Gợi ý hôm nay:</span> {primary.suggested_action}
                        </p>
                    )}
                </div>
            )}

            {(level === 'no_data' || level === 'first_signals') && (
                <div className="mt-5">
                    <Link
                        to={ROUTE_PATHS.checkin}
                        className={`inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition hover:opacity-90 ${
                            isDark ? 'bg-theme-accent text-white' : 'bg-primary text-white'
                        }`}
                    >
                        Check-in cảm xúc
                    </Link>
                </div>
            )}
        </section>
    )
}
