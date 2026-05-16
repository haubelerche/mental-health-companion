import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    LabelList,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import PixelEmptyState from '../pixel/PixelEmptyState'
import type { MoodByPeriodItem } from '../../services/dashboardService'

type Props = {
    data: MoodByPeriodItem[]
}

const PERIOD_COLORS: Record<string, { bar: string; label: string }> = {
    morning: { bar: '#fbbf24', label: '#92400e' },
    afternoon: { bar: '#34d399', label: '#065f46' },
    evening: { bar: '#818cf8', label: '#3730a3' },
    unknown: { bar: '#9ca3af', label: '#374151' },
}

function PeriodTooltip({
    active,
    payload,
}: {
    active?: boolean
    payload?: Array<{ payload: MoodByPeriodItem }>
}) {
    if (!active || !payload?.length) return null
    const item = payload[0].payload
    return (
        <div className="rounded-2xl border border-theme-border bg-theme-surface/95 p-3 text-xs shadow-xl backdrop-blur-xl">
            <p className="font-semibold text-theme-text-primary">{item.label}</p>
            <div className="mt-1.5 space-y-1 text-theme-text-secondary">
                <p>
                    Mood TB:{' '}
                    <span className="font-semibold text-theme-text-primary">
                        {item.avg_mood != null ? `${item.avg_mood}/10` : 'chưa có dữ liệu'}
                    </span>
                </p>
                {item.avg_energy != null && (
                    <p>
                        Năng lượng TB:{' '}
                        <span className="font-semibold text-theme-text-primary">{item.avg_energy}/10</span>
                    </p>
                )}
                <p>{item.count} check-in</p>
            </div>
        </div>
    )
}

export function MoodByPeriodChart({ data }: Props) {
    const hasData = data.some((item) => item.avg_mood != null)

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                    Mood theo thời điểm
                </p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">
                    Sáng, chiều, tối
                </h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    So sánh mood trung bình ở từng buổi trong ngày. Mỗi cột là trung bình của tất cả check-in trong khoảng đã chọn.
                </p>
            </div>

            {!hasData ? (
                <PixelEmptyState
                    mascot="quiet"
                    title="Chưa đủ dữ liệu để so sánh theo buổi."
                    description="Check-in vào các buổi khác nhau (sáng, chiều, tối) để thấy mood thay đổi thế nào trong ngày."
                />
            ) : (
                <>
                    <div className="h-52 min-w-0">
                        <ResponsiveContainer width="100%" height="100%" minWidth={1}>
                            <BarChart
                                data={data}
                                margin={{ top: 20, right: 12, left: -20, bottom: 0 }}
                                barCategoryGap="30%"
                            >
                                <CartesianGrid
                                    stroke="var(--theme-border)"
                                    strokeDasharray="4 10"
                                    vertical={false}
                                />
                                <XAxis
                                    dataKey="label"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: 'var(--theme-text-secondary)', fontSize: 12, fontWeight: 600 }}
                                />
                                <YAxis
                                    domain={[0, 10]}
                                    tickCount={6}
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: 'var(--theme-text-tertiary)', fontSize: 11 }}
                                />
                                <Tooltip content={<PeriodTooltip />} cursor={{ fill: 'var(--theme-border)', opacity: 0.3 }} />
                                <Bar dataKey="avg_mood" radius={[8, 8, 0, 0]} maxBarSize={72}>
                                    {data.map((item) => {
                                        const color = PERIOD_COLORS[item.period] ?? PERIOD_COLORS.unknown
                                        return <Cell key={item.period} fill={color.bar} />
                                    })}
                                    <LabelList
                                        dataKey="avg_mood"
                                        position="top"
                                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                        formatter={(val: any) =>
                                            val != null && val !== '' ? String(val) : ''
                                        }
                                        style={{ fontSize: 12, fontWeight: 700, fill: 'var(--theme-text-primary)' }}
                                    />
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-3 text-xs text-theme-text-secondary">
                        {data.map((item) => {
                            const color = PERIOD_COLORS[item.period] ?? PERIOD_COLORS.unknown
                            return (
                                <span key={item.period} className="inline-flex items-center gap-1.5">
                                    <span
                                        className="inline-block h-2.5 w-2.5 rounded-sm"
                                        style={{ backgroundColor: color.bar }}
                                    />
                                    {item.label}
                                    {item.count > 0 && (
                                        <span className="text-theme-text-tertiary">({item.count})</span>
                                    )}
                                </span>
                            )
                        })}
                    </div>
                </>
            )}
        </section>
    )
}
