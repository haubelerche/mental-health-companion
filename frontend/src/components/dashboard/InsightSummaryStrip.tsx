import { ArrowRight, BarChart3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReflectDashboardSummary } from '../../services/dashboardService'

type Props = {
    summary: ReflectDashboardSummary
}

export function InsightSummaryStrip({ summary }: Props) {
    const action = summary.recommended_action
    const evidenceLabel =
        summary.checkin_count === 0 ? 'Bằng chứng: chưa có check-in' : `Bằng chứng: ${summary.checkin_count} check-in`

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                    <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                        <BarChart3 className="h-4 w-4 text-cyan-500" aria-hidden />
                        Dựa trên dữ liệu đã ghi
                    </p>
                    <h2 className="mt-2 text-xl font-semibold leading-snug text-theme-text-primary md:text-2xl">
                        {summary.primary_observation}
                    </h2>
                    <p className="mt-2 text-sm text-theme-text-secondary">
                        {summary.data_quality === 'clear_signal' ? 'Độ tin cậy: khá rõ' : summary.data_quality === 'early_signal' ? 'Độ tin cậy: sơ bộ' : 'Độ tin cậy: thấp'} · {evidenceLabel}
                    </p>
                </div>
                {action && (
                    <div className="rounded-xl border border-theme-border/70 bg-theme-bg-secondary/70 p-3 lg:w-80">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-theme-text-tertiary">Nên bổ sung</p>
                        <p className="mt-1 text-sm font-semibold text-theme-text-primary">{action.label}</p>
                        <p className="mt-1 text-xs leading-relaxed text-theme-text-secondary">{action.reason}</p>
                        <Link
                            to={action.route}
                            className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-theme-accent"
                        >
                            Thực hiện
                            <ArrowRight className="h-4 w-4" aria-hidden />
                        </Link>
                    </div>
                )}
            </div>
        </section>
    )
}
