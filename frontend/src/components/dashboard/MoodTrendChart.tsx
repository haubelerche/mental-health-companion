import { Activity, HeartPulse } from 'lucide-react'
import {
    Area,
    AreaChart,
    CartesianGrid,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import PixelEmptyState from '../pixel/PixelEmptyState'
import type { ReflectMoodSeriesPoint } from '../../services/dashboardService'

type Props = {
    series: ReflectMoodSeriesPoint[]
    enoughForTrend: boolean
}

type ChartPoint = ReflectMoodSeriesPoint & {
    day_label: string
}

function formatDay(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-')
    if (!year || !month || !day) return value.slice(5)
    return `${day}/${month}`
}

function MoodTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartPoint }> }) {
    if (!active || !payload?.length) return null
    const point = payload[0].payload
    return (
        <div className="max-w-64 rounded-2xl border border-theme-border bg-theme-surface/95 p-3 text-xs shadow-xl backdrop-blur-xl">
            <p className="font-semibold text-theme-text-primary">{formatDay(point.date)}</p>
            <div className="mt-2 space-y-1 text-theme-text-secondary">
                <p>Cảm xúc: {point.mood_score != null ? `${point.mood_score}/10` : 'chưa ghi'}</p>
                <p>Năng lượng: {point.energy_score != null ? `${point.energy_score}/10` : 'chưa ghi'}</p>
                {point.top_emotions.length > 0 && <p>Cảm xúc nổi bật: {point.top_emotions.join(', ')}</p>}
                {point.top_triggers.length > 0 && <p>Trigger: {point.top_triggers.join(', ')}</p>}
                {point.note_excerpt && <p>Ghi chú: “{point.note_excerpt}”</p>}
            </div>
        </div>
    )
}

export function MoodTrendChart({ series, enoughForTrend }: Props) {
    const chartData: ChartPoint[] = series.map((point) => ({
        ...point,
        day_label: formatDay(point.date),
    }))
    const scores = chartData
        .map((point) => point.mood_score)
        .filter((score): score is number => typeof score === 'number')
    const hasData = scores.length > 0
    const average = hasData ? Math.round((scores.reduce((sum, score) => sum + score, 0) / scores.length) * 10) / 10 : null
    const min = hasData ? Math.min(...scores) : null
    const max = hasData ? Math.max(...scores) : null

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Nhịp cảm xúc</p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Mood theo ngày</h2>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-theme-text-secondary">
                        Đường càng cao nghĩa là điểm mood được tự ghi nhận tích cực hơn. Đường chấm thể hiện mức trung bình trong khoảng đã chọn.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-theme-text-secondary">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-theme-border px-3 py-1">
                        <HeartPulse className="h-3.5 w-3.5 text-emerald-500" aria-hidden />
                        Mood tự ghi nhận
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-theme-border px-3 py-1">
                        <Activity className="h-3.5 w-3.5 text-cyan-500" aria-hidden />
                        Năng lượng nếu có
                    </span>
                </div>
            </div>

            {!hasData ? (
                <PixelEmptyState
                    mascot="quiet"
                    title="Chưa có điểm mood để vẽ xu hướng."
                    description="Một check-in có điểm mood là đủ để bắt đầu tạo timeline."
                />
            ) : (
                <>
                    <div className="mb-4 flex flex-wrap gap-2 text-xs text-theme-text-secondary">
                        <span className="rounded-full bg-theme-bg-secondary/80 px-3 py-1">Trung bình {average}/10</span>
                        <span className="rounded-full bg-theme-bg-secondary/80 px-3 py-1">Thấp nhất {min}/10</span>
                        <span className="rounded-full bg-theme-bg-secondary/80 px-3 py-1">Cao nhất {max}/10</span>
                        {!enoughForTrend && (
                            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-800 dark:bg-amber-400/10 dark:text-amber-100">
                                Xu hướng sơ bộ
                            </span>
                        )}
                    </div>
                    <div className="h-64 min-w-0">
                        <ResponsiveContainer width="100%" height="100%" minWidth={1}>
                            <AreaChart data={chartData} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="reflectMoodGradient" x1="0" x2="0" y1="0" y2="1">
                                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.34} />
                                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.03} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid stroke="var(--theme-border)" strokeDasharray="4 10" vertical={false} />
                                <XAxis
                                    dataKey="day_label"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: 'var(--theme-text-tertiary)', fontSize: 11 }}
                                />
                                <YAxis
                                    domain={[1, 10]}
                                    tickCount={5}
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: 'var(--theme-text-tertiary)', fontSize: 11 }}
                                />
                                {average != null && (
                                    <ReferenceLine
                                        y={average}
                                        stroke="#06b6d4"
                                        strokeDasharray="4 6"
                                        strokeOpacity={0.75}
                                    />
                                )}
                                <Tooltip content={<MoodTooltip />} cursor={{ stroke: 'var(--theme-accent)', strokeOpacity: 0.2 }} />
                                <Area
                                    type="monotone"
                                    dataKey="mood_score"
                                    stroke="#10b981"
                                    strokeWidth={3}
                                    fill="url(#reflectMoodGradient)"
                                    connectNulls
                                    dot={{ r: 4, strokeWidth: 2, fill: '#10b981', stroke: 'var(--theme-surface)' }}
                                    activeDot={{ r: 6, strokeWidth: 2, fill: '#06b6d4', stroke: 'var(--theme-surface)' }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}
        </section>
    )
}
