import type { ReflectDataQuality } from '../../services/dashboardService'

type Props = {
    dataQuality: ReflectDataQuality
}

const TONE: Record<string, string> = {
    no_data: 'border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-500/30 dark:bg-slate-400/10 dark:text-slate-200',
    low_data: 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-400/25 dark:bg-amber-400/10 dark:text-amber-100',
    early_signal: 'border-cyan-300 bg-cyan-50 text-cyan-800 dark:border-cyan-400/25 dark:bg-cyan-400/10 dark:text-cyan-100',
    clear_signal:
        'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-400/25 dark:bg-emerald-400/10 dark:text-emerald-100',
}

export function DataQualityBadge({ dataQuality }: Props) {
    return (
        <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${
                TONE[dataQuality.quality]
            }`}
        >
            {dataQuality.badge_label}
        </span>
    )
}
