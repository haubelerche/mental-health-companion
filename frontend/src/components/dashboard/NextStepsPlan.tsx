import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReflectDashboardSummary, ReflectSuggestedAction } from '../../services/dashboardService'
import { ROUTE_PATHS } from '../../routes/paths'

type Props = {
    summary: ReflectDashboardSummary
}

type StepItem = {
    label: string
    reason: string
    route: string
    isPrimary: boolean
}

const SECONDARY_DEFAULTS: ReflectSuggestedAction[] = [
    {
        label: 'Check-in cảm xúc tối nay',
        route: ROUTE_PATHS.checkin,
        reason: 'Check-in buổi tối giúp so sánh mood với các thời điểm khác trong ngày.',
        action_type: 'checkin',
    },
    {
        label: 'Ghi một ghi chú ngắn',
        route: ROUTE_PATHS.chat,
        reason: 'Viết ra suy nghĩ, dù chỉ 2 câu, thường giúp nhẹ đầu hơn.',
        action_type: 'journal',
    },
]

function buildSteps(summary: ReflectDashboardSummary): StepItem[] {
    const steps: StepItem[] = []

    if (summary.recommended_action) {
        steps.push({
            label: summary.recommended_action.label,
            reason: summary.recommended_action.reason,
            route: summary.recommended_action.route,
            isPrimary: true,
        })
    } else {
        steps.push({
            label: 'Tạo check-in đầu tiên',
            reason: 'Một ghi nhận nhỏ là bước đầu tiên để Serene hiểu nhịp cảm xúc của bạn.',
            route: ROUTE_PATHS.checkin,
            isPrimary: true,
        })
    }

    const coveredRoutes = new Set([steps[0].route])
    for (const def of SECONDARY_DEFAULTS) {
        if (steps.length >= 3) break
        if (!coveredRoutes.has(def.route)) {
            steps.push({ label: def.label, reason: def.reason, route: def.route, isPrimary: false })
            coveredRoutes.add(def.route)
        }
    }

    return steps
}

export function NextStepsPlan({ summary }: Props) {
    const steps = buildSteps(summary)
    const [primary, ...secondary] = steps

    return (
        <section className="rounded-2xl border border-cyan-200 bg-theme-surface p-4 shadow-sm backdrop-blur-xl md:p-5 dark:border-cyan-400/20">
            <div className="mb-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-500" aria-hidden />
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                        Bước nhỏ hôm nay
                    </p>
                </div>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Một bước nhỏ hôm nay</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Serene gợi ý một việc phù hợp với những gì bạn đang trải qua.
                </p>
            </div>

            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm dark:border-emerald-400/25 dark:bg-emerald-400/8">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
                    Ưu tiên
                </p>
                <p className="text-base font-semibold text-theme-text-primary">{primary.label}</p>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">{primary.reason}</p>
                <Link
                    to={primary.route}
                    className="mt-3 inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700"
                >
                    Thực hiện
                    <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
            </div>

            {secondary.length > 0 && (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {secondary.map((step) => (
                        <Link
                            key={step.route}
                            to={step.route}
                            className="group flex flex-col rounded-2xl border border-theme-border bg-theme-bg-secondary p-3 transition hover:bg-theme-surface"
                        >
                            <p className="text-sm font-semibold text-theme-text-primary transition group-hover:text-emerald-700 dark:group-hover:text-emerald-300">
                                {step.label}
                            </p>
                            <p className="mt-1 text-xs leading-relaxed text-theme-text-secondary">
                                {step.reason}
                            </p>
                        </Link>
                    ))}
                </div>
            )}
        </section>
    )
}
