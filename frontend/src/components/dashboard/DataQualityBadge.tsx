import type { ReflectDataQuality } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    dataQuality: ReflectDataQuality
}

export function DataQualityBadge({ dataQuality }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const TONE: Record<string, string> = {
        no_data: isDark
            ? 'border-slate-500/30 bg-slate-400/10 text-slate-200'
            : 'border-slate-300 bg-slate-100 text-slate-700',
        low_data: isDark
            ? 'border-amber-400/25 bg-amber-400/10 text-amber-100'
            : 'border-amber-300 bg-amber-50 text-amber-800',
        early_signal: isDark
            ? 'border-cyan-400/25 bg-cyan-400/10 text-cyan-100'
            : 'border-cyan-300 bg-cyan-50 text-cyan-800',
        clear_signal: isDark
            ? 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100'
            : 'border-emerald-300 bg-emerald-50 text-emerald-800',
    }

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
