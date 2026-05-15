import { Info } from 'lucide-react'
import type { ReflectDataQuality } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    dataQuality: ReflectDataQuality
}

export function DataQualityNotice({ dataQuality }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const tone =
        dataQuality.label === 'limited'
            ? isDark
                ? 'border-white/10 bg-white/5 text-theme-text-secondary'
                : 'border-neutral-300/60 bg-neutral-100 text-neutral-700'
            : isDark
                ? 'border-emerald-400/15 bg-emerald-400/10 text-emerald-100'
                : 'border-emerald-200/70 bg-emerald-50 text-emerald-900'

    return (
        <section className={`flex gap-3 rounded-2xl border px-4 py-3 text-sm leading-relaxed ${tone}`}>
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <p>{dataQuality.user_message}</p>
        </section>
    )
}
