import { Grid3X3 } from 'lucide-react'
import PixelEmptyState from '../pixel/PixelEmptyState'
import type { TriggerEmotionMatrixCell } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    matrix: TriggerEmotionMatrixCell[]
}

function uniqueTop(values: string[], limit: number): string[] {
    return [...new Set(values)].slice(0, limit)
}

export function TriggerEmotionHeatmap({ matrix }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const STRENGTH_CLASS: Record<TriggerEmotionMatrixCell['strength'], string> = {
        low: isDark ? 'bg-emerald-300/15 text-emerald-100' : 'bg-emerald-200/35 text-emerald-900',
        medium: isDark ? 'bg-cyan-300/25 text-cyan-50' : 'bg-cyan-300/55 text-cyan-950',
        high: isDark ? 'bg-amber-300/35 text-amber-50' : 'bg-amber-300/75 text-amber-950',
    }

    const triggers = uniqueTop(matrix.map((cell) => cell.trigger), 7)
    const emotions = uniqueTop(matrix.map((cell) => cell.emotion), 6)
    const lookup = new Map(matrix.map((cell) => [`${cell.trigger}:::${cell.emotion}`, cell]))

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Pattern map</p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Trigger đi cùng cảm xúc</h2>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-theme-text-secondary">
                        Ô đậm hơn nghĩa là cặp này xuất hiện nhiều hơn trong check-in gần đây.
                    </p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full border border-theme-border px-3 py-1 text-xs text-theme-text-secondary">
                    <Grid3X3 className="h-4 w-4" aria-hidden />
                    Trigger x cảm xúc
                </span>
            </div>

            {matrix.length === 0 || triggers.length === 0 || emotions.length === 0 ? (
                <PixelEmptyState
                    mascot="quiet"
                    title="Chưa có cặp trigger-cảm xúc."
                    description="Khi check-in có cả trigger và cảm xúc, dashboard sẽ bắt đầu hiển thị các cặp xuất hiện cùng nhau."
                />
            ) : (
                <div className="overflow-x-auto pb-2">
                    <div
                        className="grid min-w-[42rem] gap-2"
                        style={{ gridTemplateColumns: `9rem repeat(${emotions.length}, minmax(5.5rem, 1fr))` }}
                    >
                        <div />
                        {emotions.map((emotion) => (
                            <div key={emotion} className="px-2 text-center text-xs font-semibold text-theme-text-secondary">
                                {emotion}
                            </div>
                        ))}
                        {triggers.map((trigger) => (
                            <div key={trigger} className="contents">
                                <div className="flex items-center rounded-xl bg-theme-bg-secondary/70 px-3 py-2 text-xs font-semibold text-theme-text-primary wrap-break-words">
                                    {trigger}
                                </div>
                                {emotions.map((emotion) => {
                                    const cell = lookup.get(`${trigger}:::${emotion}`)
                                    return (
                                        <div
                                            key={`${trigger}-${emotion}`}
                                            className={`flex h-12 items-center justify-center rounded-xl border border-theme-secondary/15 text-xs font-semibold transition duration-200 ${
                                                cell
                                                    ? STRENGTH_CLASS[cell.strength]
                                                    : isDark
                                                        ? 'bg-white/5 text-theme-text-tertiary'
                                                        : 'bg-theme-bg-secondary/45 text-theme-text-tertiary'
                                            }`}
                                            title={cell ? `${trigger} + ${emotion}: ${cell.count} lần` : `${trigger} + ${emotion}: chưa thấy`}
                                        >
                                            {cell?.count || ''}
                                        </div>
                                    )
                                })}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </section>
    )
}
