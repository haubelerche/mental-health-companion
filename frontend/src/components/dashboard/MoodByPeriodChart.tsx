import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    LabelList,
    ReferenceLine,
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

const PERIOD_COLORS: Record<string, { bar: string }> = {
    morning: { bar: '#fbbf24' },
    afternoon: { bar: '#34d399' },
    evening: { bar: '#818cf8' },
    unknown: { bar: '#9ca3af' },
}

// Matches toTenPointMood output (backend 1-5 → ×2 = 2/4/6/8/10)
const MOOD_LEVELS: Array<{ max: number; label: string }> = [
    { max: 2, label: 'Khó khăn' },
    { max: 4, label: 'Buồn' },
    { max: 6, label: 'Ổn' },
    { max: 8, label: 'Tốt' },
    { max: 10, label: 'Rất tốt' },
]

function moodLabel(score: number | null): string {
    if (score == null) return ''
    return MOOD_LEVELS.find((l) => score <= l.max)?.label ?? 'Rất tốt'
}

function weightedAvg(data: MoodByPeriodItem[]): number | null {
    const totalCount = data.reduce((s, d) => s + d.count, 0)
    if (!totalCount) return null
    const totalScore = data.reduce(
        (s, d) => (d.avg_mood != null ? s + d.avg_mood * d.count : s),
        0,
    )
    return Math.round((totalScore / totalCount) * 10) / 10
}

function getInterpretation(data: MoodByPeriodItem[]): string | null {
    const scored = data.filter((d) => d.avg_mood != null && d.count > 0)
    if (scored.length < 2) return null

    const best = scored.reduce((a, b) => (a.avg_mood! > b.avg_mood! ? a : b))
    const worst = scored.reduce((a, b) => (a.avg_mood! < b.avg_mood! ? a : b))

    if (best.avg_mood === worst.avg_mood) {
        return `Mood của bạn khá đồng đều trong ngày — cả ${scored.length} buổi ở mức "${moodLabel(best.avg_mood)}" (${best.avg_mood}/10). Hãy check-in thêm để thấy sự biến động rõ hơn.`
    }

    const delta = Math.round((best.avg_mood! - worst.avg_mood!) * 10) / 10
    return `Bạn thường cảm thấy tốt nhất vào ${best.label.toLowerCase()} (${best.avg_mood}/10 — ${moodLabel(best.avg_mood)}), thấp nhất vào ${worst.label.toLowerCase()} (${worst.avg_mood}/10 — ${moodLabel(worst.avg_mood)}), chênh nhau ${delta} điểm.`
}

function PeriodTooltip({
    active,
    payload,
    overallAvg,
}: {
    active?: boolean
    payload?: Array<{ payload: MoodByPeriodItem }>
    overallAvg: number | null
}) {
    if (!active || !payload?.length) return null
    const item = payload[0].payload
    const delta =
        overallAvg != null && item.avg_mood != null
            ? Math.round((item.avg_mood - overallAvg) * 10) / 10
            : null

    return (
        <div className="rounded-2xl border border-theme-border bg-theme-surface/95 p-3 text-xs shadow-xl backdrop-blur-xl">
            <p className="font-semibold text-theme-text-primary">{item.label}</p>
            <div className="mt-1.5 space-y-1 text-theme-text-secondary">
                <p>
                    Mood TB:{' '}
                    <span className="font-semibold text-theme-text-primary">
                        {item.avg_mood != null
                            ? `${item.avg_mood}/10 — ${moodLabel(item.avg_mood)}`
                            : 'chưa có dữ liệu'}
                    </span>
                </p>
                {delta != null && (
                    <p>
                        So với TB chung:{' '}
                        <span
                            className={`font-semibold ${
                                delta > 0
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : delta < 0
                                      ? 'text-amber-600 dark:text-amber-400'
                                      : 'text-theme-text-primary'
                            }`}
                        >
                            {delta > 0 ? `+${delta}` : delta === 0 ? '±0' : `${delta}`}
                        </span>
                    </p>
                )}
                <p>{item.count} lần check-in trong buổi này</p>
                <p className="text-theme-text-tertiary">
                    Cách tính: TB điểm mood của {item.count} check-in{item.count > 1 ? '' : ' này'} trong khoảng đã chọn.
                </p>
            </div>
        </div>
    )
}

export function MoodByPeriodChart({ data }: Props) {
    const hasData = data.some((item) => item.avg_mood != null)
    const overallAvg = weightedAvg(data)
    const interpretation = getInterpretation(data)

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                    Mood theo thời điểm
                </p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Sáng, chiều, tối</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Trung bình mood từng buổi trong khoảng đã chọn — thang 10 điểm:{' '}
                    <span className="font-medium text-theme-text-primary">2 Khó khăn · 4 Buồn · 6 Ổn · 8 Tốt · 10 Rất tốt</span>.{' '}
                    Đường ngang là mức trung bình chung của bạn.
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
                                margin={{ top: 20, right: 16, left: -20, bottom: 0 }}
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
                                <Tooltip
                                    content={<PeriodTooltip overallAvg={overallAvg} />}
                                    cursor={{ fill: 'var(--theme-border)', opacity: 0.3 }}
                                />
                                {overallAvg != null && (
                                    <ReferenceLine
                                        y={overallAvg}
                                        stroke="var(--theme-accent)"
                                        strokeDasharray="5 4"
                                        strokeWidth={1.5}
                                        label={{
                                            value: `TB: ${overallAvg}`,
                                            position: 'insideTopRight',
                                            fill: 'var(--theme-accent)',
                                            fontSize: 11,
                                            fontWeight: 700,
                                        }}
                                    />
                                )}
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
                                        <span className="text-theme-text-tertiary">
                                            ({item.count} check-in
                                            {item.avg_mood != null
                                                ? ` · ${moodLabel(item.avg_mood)}`
                                                : ''})
                                        </span>
                                    )}
                                </span>
                            )
                        })}
                    </div>

                    {interpretation && (
                        <p className="mt-3 rounded-xl bg-theme-bg-secondary px-3 py-2.5 text-xs leading-relaxed text-theme-text-secondary">
                            {interpretation}
                        </p>
                    )}
                </>
            )}
        </section>
    )
}
