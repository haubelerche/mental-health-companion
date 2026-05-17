import { ArrowRight, CalendarClock, Leaf, Sparkles, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReflectDashboardResponse } from '../../services/dashboardService'

type Props = {
    dashboard: ReflectDashboardResponse
}

function formatUpdatedAt(value: string): string {
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return 'vừa xong'
    return parsed.toLocaleString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: '2-digit',
    })
}

function sparklinePoints(values: Array<number | null>): string {
    const scored = values.filter((value): value is number => typeof value === 'number')
    if (!scored.length) return ''
    const min = Math.min(...scored)
    const max = Math.max(...scored)
    const span = Math.max(1, max - min)
    return values
        .map((value, index) => {
            const x = values.length <= 1 ? 0 : (index / (values.length - 1)) * 120
            const y = typeof value === 'number' ? 56 - ((value - min) / span) * 42 : 56
            return `${x.toFixed(1)},${y.toFixed(1)}`
        })
        .join(' ')
}

export function WellnessOverviewHero({ dashboard }: Props) {
    const { overview, data_quality: dataQuality } = dashboard
    const points = sparklinePoints(dashboard.mood_series.map((point) => point.mood_score))

    return (
        <section className="relative overflow-hidden rounded-[2rem] border border-emerald-100/80 bg-gradient-to-br from-[#ddf7ed] via-[#d9f4f4] to-[#f2fbf5] p-5 shadow-sm shadow-emerald-900/5 backdrop-blur-xl">
            <div
                className="pointer-events-none absolute inset-0 opacity-[0.16]"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(40,130,115,.28) 1px, transparent 1px), linear-gradient(90deg, rgba(40,130,115,.28) 1px, transparent 1px)',
                    backgroundSize: '18px 18px',
                }}
            />
            <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-center">
                <div>
                    <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200/80 bg-white/60 px-3 py-1 text-xs font-semibold text-emerald-900 shadow-sm shadow-emerald-900/5">
                        <Sparkles className="h-3.5 w-3.5" aria-hidden />
                        Tình hình hiện tại
                    </div>
                    <h2 className="max-w-3xl font-display text-3xl leading-tight text-[#17352f] md:text-4xl">
                        {overview.state_label === 'Dữ liệu còn ít'
                            ? 'Serene cần thêm dữ liệu thật để nhận định chính xác.'
                            : `Tuần này bạn ${overview.state_label.toLowerCase()}.`}
                    </h2>
                    <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[#31554d] md:text-base">
                        {overview.summary}
                    </p>
                    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        <div className="rounded-2xl border border-white/70 bg-white/60 p-3 shadow-sm shadow-emerald-900/5">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#5f776f]">
                                Tình hình chung
                            </p>
                            <p className="mt-2 text-sm font-semibold text-[#17352f]">{overview.state_label}</p>
                        </div>
                        <div className="rounded-2xl border border-white/70 bg-white/60 p-3 shadow-sm shadow-emerald-900/5">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#5f776f]">
                                Xu hướng
                            </p>
                            <p className="mt-2 text-sm font-semibold text-[#17352f]">{overview.trend_label}</p>
                        </div>
                        <div className="rounded-2xl border border-white/70 bg-white/60 p-3 shadow-sm shadow-emerald-900/5">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#5f776f]">
                                Yếu tố nổi bật
                            </p>
                            <p className="mt-2 text-sm font-semibold text-[#17352f]">
                                {overview.primary_factor || 'Chưa rõ'}
                            </p>
                        </div>
                        <div className="rounded-2xl border border-white/70 bg-white/60 p-3 shadow-sm shadow-emerald-900/5">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#5f776f]">
                                Một bước hôm nay
                            </p>
                            {overview.suggested_action ? (
                                <Link
                                    to={overview.suggested_action.route}
                                    className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-emerald-700 hover:text-emerald-800"
                                >
                                    {overview.suggested_action.label}
                                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                                </Link>
                            ) : (
                                <p className="mt-2 text-sm font-semibold text-[#17352f]">Check-in nhẹ</p>
                            )}
                        </div>
                    </div>
                </div>

                <div className="rounded-3xl border border-white/70 bg-white/55 p-4 shadow-sm shadow-emerald-900/5">
                    <div className="flex items-center justify-between gap-3 text-xs text-[#31554d]">
                        <span className="inline-flex items-center gap-1.5">
                            <TrendingUp className="h-4 w-4 text-cyan-600" aria-hidden />
                            Nhịp gần đây
                        </span>
                        <span>{dataQuality.checkin_count} check-in</span>
                    </div>
                    <div className="mt-5 h-20">
                        {points ? (
                            <svg viewBox="0 0 120 64" className="h-full w-full overflow-visible" aria-hidden>
                                <polyline
                                    points={points}
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    className="text-cyan-500"
                                />
                            </svg>
                        ) : (
                            <div className="flex h-full items-center justify-center rounded-2xl bg-white/50 text-xs text-[#31554d]">
                                Chưa đủ điểm để vẽ nhịp
                            </div>
                        )}
                    </div>
                    <div className="mt-4 flex items-center gap-2 text-xs text-[#31554d]">
                        <CalendarClock className="h-4 w-4" aria-hidden />
                        Cập nhật: {formatUpdatedAt(dashboard.generated_at)}
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-xs text-[#31554d]">
                        <Leaf className="h-4 w-4" aria-hidden />
                        Quan sát nhẹ, không phải chẩn đoán
                    </div>
                </div>
            </div>
        </section>
    )
}
