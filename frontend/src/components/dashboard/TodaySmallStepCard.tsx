import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReflectSuggestedAction } from '../../services/dashboardService'

type Props = {
    action?: ReflectSuggestedAction
}

export function TodaySmallStepCard({ action }: Props) {
    if (!action) return null

    return (
        <section className="rounded-2xl border border-cyan-200/70 bg-gradient-to-br from-cyan-50/90 via-white/90 to-emerald-50/85 p-4 shadow-sm dark:border-cyan-400/15 dark:from-cyan-400/10 dark:via-theme-surface dark:to-emerald-400/10 md:p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="max-w-2xl">
                    <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden />
                        Hành động đề xuất
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-theme-text-primary">{action.label}</h2>
                    <p className="mt-2 text-sm leading-relaxed text-theme-text-secondary">{action.reason}</p>
                </div>
                <Link
                    to={action.route}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-theme-accent px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                >
                    Thực hiện
                    <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
            </div>
        </section>
    )
}
