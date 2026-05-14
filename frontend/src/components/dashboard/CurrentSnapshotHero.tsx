import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Mascot } from '../pixel/Mascot'
import type { ReflectDashboardResponse } from '../../services/dashboardService'

type Props = {
    dashboard: ReflectDashboardResponse
}

type State = 'stable' | 'improving' | 'needs_attention' | 'limited_data'

function resolveState(stateLabel: string, enoughForTrend: boolean): State {
    if (!enoughForTrend) return 'limited_data'
    if (stateLabel.includes('Ổn hơn') || stateLabel.includes('cải thiện')) return 'improving'
    if (stateLabel.includes('Cần chăm') || stateLabel.includes('chú ý')) return 'needs_attention'
    return 'stable'
}

const HEADLINE: Record<State, string> = {
    stable: 'Tuần này bạn đang ổn định hơn một chút.',
    improving: 'Tuần này bạn đang có xu hướng tốt hơn.',
    needs_attention: 'Tuần này có vài dấu hiệu bạn nên chăm thêm.',
    limited_data: 'Serene đang bắt đầu ghép nhịp cảm xúc của bạn.',
}

const BG: Record<State, string> = {
    stable: 'from-[#eef7f0] via-[#f0f8f4] to-[#f4fbf7]',
    improving: 'from-[#e8f5f0] via-[#ebf8f4] to-[#f0fbf6]',
    needs_attention: 'from-[#fef8ee] via-[#fdf4e8] to-[#fef9f0]',
    limited_data: 'from-[#f4f4f7] via-[#f5f5f8] to-[#f8f8fb]',
}

const BORDER: Record<State, string> = {
    stable: 'border-emerald-100/80',
    improving: 'border-cyan-100/80',
    needs_attention: 'border-amber-200/80',
    limited_data: 'border-gray-200/80',
}

const MASCOT_VARIANT: Record<State, 'main' | 'sunflower' | 'idle' | 'quiet'> = {
    stable: 'sunflower',
    improving: 'main',
    needs_attention: 'idle',
    limited_data: 'quiet',
}

function DataBasis({ dashboard }: { dashboard: ReflectDashboardResponse }) {
    const { data_quality: q, summary: s } = dashboard
    const parts: string[] = []
    if (q.checkin_count > 0) parts.push(`${q.checkin_count} check-in`)
    if (s.top_triggers.length > 0) parts.push(`${s.top_triggers.length} trigger ghi nhận`)
    if (dashboard.dimensions.some((d) => d.dimension === 'sleep' && d.evidence_count > 0)) parts.push('dữ liệu ngủ')
    return (
        <p className="mt-4 rounded-xl border border-white/60 bg-white/40 px-3 py-2 text-xs leading-relaxed text-[#5f776f]">
            Dựa trên{' '}
            {parts.length ? parts.join(', ') : 'dữ liệu hiện có'}
            {'. '}
            Quan sát chỉ để tự theo dõi — không phải chẩn đoán y khoa.
        </p>
    )
}

export function CurrentSnapshotHero({ dashboard }: Props) {
    const { overview, data_quality: q, summary: s } = dashboard
    const state = resolveState(overview.state_label, q.enough_for_trend)

    const topEmotion = s.top_emotions[0]?.label
    const topTrigger = s.top_triggers[0]?.label
    const supportive = dashboard.dimensions.find(
        (d) => d.status === 'steady' && d.dimension !== 'emotion',
    )?.label

    return (
        <section
            className={`relative overflow-hidden rounded-[2rem] border bg-gradient-to-br ${BG[state]} ${BORDER[state]} p-5 shadow-sm`}
        >
            {/* pixel grid overlay */}
            <div
                className="pointer-events-none absolute inset-0 opacity-[0.07]"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(77,99,89,.4) 1px, transparent 1px), linear-gradient(90deg, rgba(77,99,89,.4) 1px, transparent 1px)',
                    backgroundSize: '20px 20px',
                }}
            />

            <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start">
                {/* mascot column */}
                <div className="shrink-0 self-start">
                    <Mascot
                        variant={MASCOT_VARIANT[state]}
                        size="xl"
                        decorative
                        className="drop-shadow-sm"
                    />
                </div>

                {/* main content */}
                <div className="min-w-0 flex-1">
                    <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-[#5f776f]">
                        Tình hình hiện tại
                    </div>
                    <h2 className="font-display text-2xl leading-snug text-[#17352f] md:text-3xl">
                        {HEADLINE[state]}
                    </h2>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#31554d]">
                        {overview.summary}
                    </p>

                    {/* 4 status chips */}
                    <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                        <Chip label="Tình hình" value={overview.state_label} />
                        <Chip label="Khó khăn nổi bật" value={topTrigger ?? 'Chưa rõ'} />
                        <Chip label="Điểm tựa" value={supportive ?? topEmotion ?? 'Cần thêm dữ liệu'} />
                        {overview.suggested_action ? (
                            <div className="rounded-2xl border border-white/60 bg-white/55 p-3 shadow-sm">
                                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#5f776f]">
                                    Bước hôm nay
                                </p>
                                <Link
                                    to={overview.suggested_action.route}
                                    className="mt-1.5 inline-flex items-center gap-1 text-sm font-semibold text-emerald-700 hover:text-emerald-800"
                                >
                                    {overview.suggested_action.label}
                                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                                </Link>
                            </div>
                        ) : (
                            <Chip label="Bước hôm nay" value="Check-in nhẹ" />
                        )}
                    </div>

                    <DataBasis dashboard={dashboard} />
                </div>
            </div>
        </section>
    )
}

function Chip({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-white/60 bg-white/55 p-3 shadow-sm">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#5f776f]">{label}</p>
            <p className="mt-1.5 text-sm font-semibold text-[#17352f]">{value}</p>
        </div>
    )
}
