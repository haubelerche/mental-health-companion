import { History } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ReflectRecentCheckin } from '../../services/dashboardService'
import { ROUTE_PATHS } from '../../routes/paths'

type Props = {
    checkins: ReflectRecentCheckin[]
}

type EvidenceFilter = 'all' | 'mood' | 'trigger' | 'nutrition' | 'memory'

const FILTERS: Array<{ value: EvidenceFilter; label: string }> = [
    { value: 'all', label: 'Tất cả' },
    { value: 'mood', label: 'Mood' },
    { value: 'trigger', label: 'Trigger' },
    { value: 'nutrition', label: 'Nutrition' },
    { value: 'memory', label: 'Memory' },
]

const PERIOD_LABEL: Record<ReflectRecentCheckin['period'], string> = {
    morning: 'Sáng',
    afternoon: 'Chiều',
    evening: 'Tối',
    unknown: 'Chưa ghi',
}

function formatDate(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-')
    if (!year || !month || !day) return value
    return `${day}/${month}`
}

function compactList(values: string[]): string {
    if (!values.length) return 'Chưa ghi'
    return values.slice(0, 3).join(', ')
}

function note(value?: string): string {
    if (!value) return 'Chưa ghi'
    return value.length > 80 ? `${value.slice(0, 77)}...` : value
}

function filterRows(checkins: ReflectRecentCheckin[], filter: EvidenceFilter): ReflectRecentCheckin[] {
    if (filter === 'mood') return checkins.filter((item) => item.mood_score != null)
    if (filter === 'trigger') return checkins.filter((item) => item.triggers.length > 0)
    if (filter === 'nutrition' || filter === 'memory') return []
    return checkins
}

export function RecentCheckinsTable({ checkins }: Props) {
    const [filter, setFilter] = useState<EvidenceFilter>('all')
    const rows = useMemo(
        () => filterRows([...checkins].sort((a, b) => b.date.localeCompare(a.date)), filter),
        [checkins, filter],
    )

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Bằng chứng</p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Check-in gần đây</h2>
                    <p className="mt-2 max-w-2xl text-sm leading-relaxed text-theme-text-secondary">
                        Bảng này chỉ hiển thị evidence đã được rút gọn từ dữ liệu người dùng tự ghi trong dashboard.
                    </p>
                </div>
                <Link
                    to={ROUTE_PATHS.checkin}
                    className="inline-flex items-center gap-2 rounded-full bg-theme-accent px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                >
                    <History className="h-4 w-4" aria-hidden />
                    Check-in mới
                </Link>
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
                {FILTERS.map((item) => (
                    <button
                        key={item.value}
                        type="button"
                        onClick={() => setFilter(item.value)}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                            filter === item.value
                                ? 'border-theme-accent bg-theme-accent text-white'
                                : 'border-theme-border bg-theme-bg-secondary/70 text-theme-text-secondary hover:text-theme-text-primary'
                        }`}
                    >
                        {item.label}
                    </button>
                ))}
            </div>

            {rows.length === 0 ? (
                <div className="rounded-xl bg-theme-bg-secondary/70 p-4 text-sm text-theme-text-secondary">
                    {filter === 'nutrition' || filter === 'memory'
                        ? 'Chưa có evidence loại này trong endpoint hiện tại.'
                        : 'Chưa có check-in trong khung thời gian này.'}
                </div>
            ) : (
                <>
                    <div className="hidden overflow-x-auto md:block">
                        <table className="min-w-[52rem] w-full border-separate border-spacing-y-2 text-left text-sm">
                            <thead className="text-xs uppercase tracking-[0.14em] text-theme-text-tertiary">
                                <tr>
                                    <th className="px-3 py-2 font-semibold">Ngày</th>
                                    <th className="px-3 py-2 font-semibold">Buổi</th>
                                    <th className="px-3 py-2 text-right font-semibold">Mood</th>
                                    <th className="px-3 py-2 text-right font-semibold">Năng lượng</th>
                                    <th className="px-3 py-2 font-semibold">Trigger</th>
                                    <th className="px-3 py-2 font-semibold">Cảm xúc</th>
                                    <th className="px-3 py-2 font-semibold">Ghi chú an toàn</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((checkin) => (
                                    <tr key={checkin.id} className="bg-theme-bg-secondary/65 text-theme-text-secondary">
                                        <td className="rounded-l-xl px-3 py-3 font-semibold text-theme-text-primary">
                                            {formatDate(checkin.date)}
                                        </td>
                                        <td className="px-3 py-3">{PERIOD_LABEL[checkin.period]}</td>
                                        <td className="px-3 py-3 text-right tabular-nums">
                                            {checkin.mood_score != null ? `${checkin.mood_score}/10` : 'Chưa ghi'}
                                        </td>
                                        <td className="px-3 py-3 text-right tabular-nums">
                                            {checkin.energy_score != null ? `${checkin.energy_score}/10` : 'Chưa ghi'}
                                        </td>
                                        <td className="px-3 py-3">{compactList(checkin.triggers)}</td>
                                        <td className="px-3 py-3">{compactList(checkin.emotions)}</td>
                                        <td className="rounded-r-xl px-3 py-3">{note(checkin.note_excerpt)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="grid gap-3 md:hidden">
                        {rows.map((checkin) => (
                            <article key={checkin.id} className="rounded-xl border border-theme-border/70 bg-theme-bg-secondary/70 p-3">
                                <div className="flex items-center justify-between">
                                    <p className="font-semibold text-theme-text-primary">{formatDate(checkin.date)}</p>
                                    <p className="text-xs text-theme-text-secondary">{PERIOD_LABEL[checkin.period]}</p>
                                </div>
                                <p className="mt-2 text-sm text-theme-text-secondary">
                                    Mood: {checkin.mood_score != null ? `${checkin.mood_score}/10` : 'Chưa ghi'} · Năng lượng:{' '}
                                    {checkin.energy_score != null ? `${checkin.energy_score}/10` : 'Chưa ghi'}
                                </p>
                                <p className="mt-1 text-sm text-theme-text-secondary">Trigger: {compactList(checkin.triggers)}</p>
                                <p className="mt-1 text-sm text-theme-text-secondary">Cảm xúc: {compactList(checkin.emotions)}</p>
                                <p className="mt-1 text-sm text-theme-text-secondary">Ghi chú: {note(checkin.note_excerpt)}</p>
                            </article>
                        ))}
                    </div>
                </>
            )}
        </section>
    )
}
