import type { ReactNode } from 'react'

type Props = {
    label: string
    value: ReactNode
    detail?: ReactNode
}

export function ReflectMetricCard({ label, value, detail }: Props) {
    return (
        <article className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-theme-text-tertiary">{label}</p>
            <div className="mt-2 text-2xl font-semibold text-theme-text-primary">{value}</div>
            {detail && <div className="mt-2 text-sm leading-relaxed text-theme-text-secondary">{detail}</div>}
        </article>
    )
}
