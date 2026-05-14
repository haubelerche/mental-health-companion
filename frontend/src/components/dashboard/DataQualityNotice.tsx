import { Info } from 'lucide-react'
import type { ReflectDataQuality } from '../../services/dashboardService'

type Props = {
    dataQuality: ReflectDataQuality
}

export function DataQualityNotice({ dataQuality }: Props) {
    const tone =
        dataQuality.label === 'limited'
            ? 'border-neutral-300/60 bg-neutral-100/70 text-neutral-700 dark:border-white/10 dark:bg-white/5 dark:text-theme-text-secondary'
            : 'border-emerald-200/70 bg-emerald-50/70 text-emerald-900 dark:border-emerald-400/15 dark:bg-emerald-400/10 dark:text-emerald-100'

    return (
        <section className={`flex gap-3 rounded-2xl border px-4 py-3 text-sm leading-relaxed ${tone}`}>
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <p>{dataQuality.user_message}</p>
        </section>
    )
}
