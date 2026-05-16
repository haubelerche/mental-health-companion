import type { ReflectDashboardResponse } from '../../services/dashboardService'
import { MoodMiniTimeline } from './MoodMiniTimeline'
import { MoodTrendChart } from './MoodTrendChart'
import { TriggerEmotionHeatmap } from './TriggerEmotionHeatmap'

type Props = {
    dashboard: ReflectDashboardResponse
}

export function AdaptiveReflectVisualization({ dashboard }: Props) {
    const pairCount = dashboard.trigger_emotion_matrix.reduce((sum, item) => sum + item.count, 0)

    if (dashboard.summary.checkin_count < 3) {
        return <MoodMiniTimeline checkins={dashboard.recent_checkins} missingData={dashboard.summary.missing_data} />
    }

    return (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(21rem,0.85fr)]">
            <MoodTrendChart series={dashboard.mood_series} enoughForTrend={dashboard.data_quality.enough_for_trend} />
            {pairCount >= 3 ? (
                <TriggerEmotionHeatmap matrix={dashboard.trigger_emotion_matrix} />
            ) : (
                <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Pattern map</p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Cặp trigger-cảm xúc</h2>
                    <p className="mt-2 text-sm leading-relaxed text-theme-text-secondary">
                        Chưa đủ cặp lặp lại để dùng heatmap. Các tín hiệu hiện có được giữ ở dạng danh sách ngắn.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                        {dashboard.trigger_emotion_matrix.length ? (
                            dashboard.trigger_emotion_matrix.slice(0, 6).map((item) => (
                                <span
                                    key={`${item.trigger}-${item.emotion}`}
                                    className="rounded-full border border-theme-border bg-theme-bg-secondary/80 px-3 py-1 text-xs font-semibold text-theme-text-secondary"
                                >
                                    {item.trigger} · {item.emotion} ({item.count})
                                </span>
                            ))
                        ) : (
                            <span className="text-sm text-theme-text-secondary">Chưa có trigger và cảm xúc đi kèm.</span>
                        )}
                    </div>
                </section>
            )}
        </div>
    )
}
