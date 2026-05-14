import type { ReflectInsight } from '../../services/dashboardService'
import { InsightCard } from './InsightCard'

type Props = {
    insights: ReflectInsight[]
}

export function InsightCardList({ insights }: Props) {
    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/88 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Insight an toàn</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Nhận định có bằng chứng</h2>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-theme-text-secondary">
                    Chỉ hiển thị summary đã được backend sanitize, kèm evidence count, confidence và khoảng dữ liệu.
                </p>
            </div>
            {insights.length === 0 ? (
                <div className="rounded-xl bg-theme-bg-secondary/70 p-4 text-sm text-theme-text-secondary">
                    Chưa có insight tổng hợp từ backend trong khoảng này. Các quan sát từ check-in vẫn được hiển thị ở phần trên.
                </div>
            ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                    {insights.map((insight) => (
                        <InsightCard key={insight.insight_id} insight={insight} />
                    ))}
                </div>
            )}
        </section>
    )
}
