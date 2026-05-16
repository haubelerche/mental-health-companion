import type { ReflectDataQuality } from '../../services/dashboardService'

type Props = {
    dataQuality: ReflectDataQuality
}

const TONE: Record<string, string> = {
    no_data: 'border-slate-400 bg-slate-200 text-slate-800 dark:border-slate-400/40 dark:bg-slate-500/20 dark:text-slate-100',
    low_data: 'border-amber-400 bg-amber-100 text-amber-900 dark:border-amber-400/30 dark:bg-amber-400/15 dark:text-amber-100',
    early_signal: 'border-cyan-400 bg-cyan-100 text-cyan-900 dark:border-cyan-400/30 dark:bg-cyan-400/15 dark:text-cyan-100',
    clear_signal: 'border-emerald-400 bg-emerald-100 text-emerald-900 dark:border-emerald-400/30 dark:bg-emerald-400/15 dark:text-emerald-100',
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
