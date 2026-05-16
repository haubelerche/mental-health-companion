import { useState } from 'react'
import { X } from 'lucide-react'
import type { ReflectMoodSeriesPoint, ReflectRange } from '../../services/dashboardService'

type MoodFace = 'very-happy' | 'happy' | 'okay' | 'tired' | 'sad' | 'missing'

function getMoodFace(score: number | null | undefined): MoodFace {
    if (score == null) return 'missing'
    if (score >= 8.5) return 'very-happy'
    if (score >= 6.5) return 'happy'
    if (score >= 4.5) return 'okay'
    if (score >= 2.5) return 'tired'
    return 'sad'
}

const FACE_COLORS: Record<MoodFace, { bg: string; stroke: string; eyeFill: string; mouthFill: string }> = {
    'very-happy': { bg: '#FFE066', stroke: '#C9A000', eyeFill: '#3B3028', mouthFill: '#3B3028' },
    happy: { bg: '#FFD97D', stroke: '#C9920A', eyeFill: '#3B3028', mouthFill: '#3B3028' },
    okay: { bg: '#E8DFC8', stroke: '#A09070', eyeFill: '#5a4f3f', mouthFill: '#5a4f3f' },
    tired: { bg: '#C8D8C0', stroke: '#7A9870', eyeFill: '#3B3028', mouthFill: '#3B3028' },
    sad: { bg: '#B8C8D8', stroke: '#708090', eyeFill: '#3B3028', mouthFill: '#3B3028' },
    missing: { bg: 'transparent', stroke: '#C8C0B8', eyeFill: '#C8C0B8', mouthFill: '#C8C0B8' },
}

function PixelFaceSvg({ face, size = 36 }: { face: MoodFace; size?: number }) {
    const c = FACE_COLORS[face]
    const s = size

    if (face === 'missing') {
        return (
            <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="16" fill="none" stroke={c.stroke} strokeWidth="2" strokeDasharray="4 3" />
                <text x="18" y="23" textAnchor="middle" fontSize="13" fill={c.stroke} fontFamily="monospace">—</text>
            </svg>
        )
    }

    if (face === 'very-happy') {
        return (
            <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg" shapeRendering="crispEdges">
                <circle cx="18" cy="18" r="16" fill={c.bg} stroke={c.stroke} strokeWidth="1.5" />
                {/* star eyes */}
                <text x="11" y="20" textAnchor="middle" fontSize="9" fill={c.eyeFill} fontFamily="monospace">★</text>
                <text x="25" y="20" textAnchor="middle" fontSize="9" fill={c.eyeFill} fontFamily="monospace">★</text>
                {/* big smile */}
                <path d="M 10 22 Q 18 30 26 22" fill="none" stroke={c.mouthFill} strokeWidth="2.5" strokeLinecap="round" />
            </svg>
        )
    }

    if (face === 'happy') {
        return (
            <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="16" fill={c.bg} stroke={c.stroke} strokeWidth="1.5" />
                {/* round open eyes */}
                <circle cx="12" cy="15" r="2.5" fill={c.eyeFill} />
                <circle cx="24" cy="15" r="2.5" fill={c.eyeFill} />
                {/* smile */}
                <path d="M 11 22 Q 18 28 25 22" fill="none" stroke={c.mouthFill} strokeWidth="2" strokeLinecap="round" />
            </svg>
        )
    }

    if (face === 'okay') {
        return (
            <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="16" fill={c.bg} stroke={c.stroke} strokeWidth="1.5" />
                {/* dot eyes */}
                <circle cx="12" cy="15" r="2" fill={c.eyeFill} />
                <circle cx="24" cy="15" r="2" fill={c.eyeFill} />
                {/* flat mouth */}
                <line x1="12" y1="24" x2="24" y2="24" stroke={c.mouthFill} strokeWidth="2" strokeLinecap="round" />
            </svg>
        )
    }

    if (face === 'tired') {
        return (
            <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="16" fill={c.bg} stroke={c.stroke} strokeWidth="1.5" />
                {/* half-closed eyes */}
                <path d="M 9 14 Q 12 12 15 14" fill="none" stroke={c.eyeFill} strokeWidth="2" strokeLinecap="round" />
                <path d="M 21 14 Q 24 12 27 14" fill="none" stroke={c.eyeFill} strokeWidth="2" strokeLinecap="round" />
                {/* slight frown */}
                <path d="M 12 25 Q 18 22 24 25" fill="none" stroke={c.mouthFill} strokeWidth="2" strokeLinecap="round" />
            </svg>
        )
    }

    // sad
    return (
        <svg width={s} height={s} viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
            <circle cx="18" cy="18" r="16" fill={c.bg} stroke={c.stroke} strokeWidth="1.5" />
            {/* sad dot eyes */}
            <circle cx="12" cy="15" r="2" fill={c.eyeFill} />
            <circle cx="24" cy="15" r="2" fill={c.eyeFill} />
            {/* frown */}
            <path d="M 12 26 Q 18 21 24 26" fill="none" stroke={c.mouthFill} strokeWidth="2" strokeLinecap="round" />
            {/* tear */}
            <ellipse cx="12" cy="20" rx="1.5" ry="2.5" fill="#9FCDE3" opacity="0.8" />
        </svg>
    )
}

const VI_DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

function buildCalendarDays(series: ReflectMoodSeriesPoint[], range: ReflectRange): Array<{
    date: string | null
    point: ReflectMoodSeriesPoint | null
}> {
    const days = range === '7d' ? 7 : range === '14d' ? 14 : 30
    const byDate = new Map(series.map((pt) => [pt.date.slice(0, 10), pt]))
    const result: Array<{ date: string | null; point: ReflectMoodSeriesPoint | null }> = []

    const today = new Date()
    today.setHours(0, 0, 0, 0)

    // find start of calendar (beginning of the week containing the window start)
    const windowStart = new Date(today)
    windowStart.setDate(today.getDate() - days + 1)

    // pad to Monday
    const dow = (windowStart.getDay() + 6) % 7 // 0=Mon
    for (let i = 0; i < dow; i++) result.push({ date: null, point: null })

    for (let i = 0; i < days; i++) {
        const d = new Date(windowStart)
        d.setDate(windowStart.getDate() + i)
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
        const isFuture = d > today
        result.push({
            date: isFuture ? null : iso,
            point: byDate.get(iso) ?? null,
        })
    }

    // pad tail to full week
    while (result.length % 7 !== 0) result.push({ date: null, point: null })

    return result
}

type DayDetailProps = {
    date: string
    point: ReflectMoodSeriesPoint | null
    onClose: () => void
}

function formatVi(iso: string): string {
    const [year, month, day] = iso.split('-')
    return `${day}/${month}/${year}`
}

function DayDetail({ date, point, onClose }: DayDetailProps) {
    return (
        <div className="animate-in fade-in slide-in-from-bottom-2 mt-3 rounded-2xl border border-theme-border/70 bg-theme-surface/80 p-4 shadow-lg backdrop-blur duration-150">
            <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-semibold text-[#17352f]">{formatVi(date)}</p>
                <button
                    type="button"
                    onClick={onClose}
                    className="rounded-full p-1 text-[#5f776f] hover:bg-emerald-50"
                    aria-label="Đóng"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>
            {point ? (
                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
                    <div>
                        <dt className="text-[#7a9070]">Cảm xúc</dt>
                        <dd className="mt-0.5 font-semibold text-[#17352f]">
                            {point.mood_score != null ? `${point.mood_score}/10` : '—'}
                        </dd>
                    </div>
                    <div>
                        <dt className="text-[#7a9070]">Năng lượng</dt>
                        <dd className="mt-0.5 font-semibold text-[#17352f]">
                            {point.energy_score != null ? `${point.energy_score}/10` : '—'}
                        </dd>
                    </div>
                    {point.top_emotions.length > 0 && (
                        <div className="col-span-2">
                            <dt className="text-[#7a9070]">Cảm xúc nổi bật</dt>
                            <dd className="mt-0.5 font-semibold text-[#17352f]">{point.top_emotions.join(', ')}</dd>
                        </div>
                    )}
                    {point.top_triggers.length > 0 && (
                        <div className="col-span-2">
                            <dt className="text-[#7a9070]">Trigger</dt>
                            <dd className="mt-0.5 font-semibold text-[#17352f]">{point.top_triggers.join(', ')}</dd>
                        </div>
                    )}
                    {point.note_excerpt && (
                        <div className="col-span-2">
                            <dt className="text-[#7a9070]">Ghi chú</dt>
                            <dd className="mt-0.5 italic text-[#31554d]">"{point.note_excerpt}"</dd>
                        </div>
                    )}
                </dl>
            ) : (
                <p className="text-xs text-[#7a9070]">Ngày này chưa có check-in.</p>
            )}
        </div>
    )
}

type Props = {
    series: ReflectMoodSeriesPoint[]
    range: ReflectRange
}

export function PixelMoodCalendar({ series, range }: Props) {
    const [selected, setSelected] = useState<string | null>(null)
    const days = buildCalendarDays(series, range)
    const selectedPoint = series.find((pt) => pt.date.slice(0, 10) === selected) ?? null

    const today = new Date()
    const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Lịch cảm xúc</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Mood theo ngày</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Bấm vào một ngày để xem chi tiết.
                </p>
            </div>

            {/* day-of-week header */}
            <div className="grid grid-cols-7 gap-1.5 text-center text-[11px] font-semibold text-theme-text-tertiary mb-2">
                {VI_DAYS.map((d) => <div key={d}>{d}</div>)}
            </div>

            {/* calendar grid */}
            <div className="grid grid-cols-7 gap-1.5">
                {days.map((cell, idx) => {
                    if (!cell.date) {
                        return <div key={`empty-${idx}`} className="aspect-square" />
                    }
                    const face = getMoodFace(cell.point?.mood_score)
                    const isToday = cell.date === todayIso
                    const isSelected = cell.date === selected

                    return (
                        <button
                            key={cell.date}
                            type="button"
                            onClick={() => setSelected(isSelected ? null : cell.date)}
                            className={`flex border border-theme-secondary/10 aspect-square flex-col items-center justify-center rounded-xl transition duration-150 hover:scale-105 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                                isSelected
                                    ? 'bg-emerald-100 ring-2 ring-emerald-400 shadow-sm'
                                    : isToday
                                      ? 'bg-emerald-50/80 ring-1 ring-emerald-300/60'
                                      : 'hover:bg-theme-bg-secondary/60'
                            }`}
                            aria-label={`${cell.date}${cell.point ? `, mood ${cell.point.mood_score}/10` : ', chưa check-in'}`}
                            aria-pressed={isSelected}
                        >
                            <PixelFaceSvg face={face} size={28} />
                            <span className="mt-0.5 text-[9px] font-medium text-theme-text-tertiary leading-none">
                                {cell.date.slice(8)}
                            </span>
                        </button>
                    )
                })}
            </div>

            {/* legend */}
            <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px] text-theme-text-secondary">
                {(['very-happy', 'happy', 'okay', 'tired', 'sad', 'missing'] as MoodFace[]).map((face) => {
                    const labels: Record<MoodFace, string> = {
                        'very-happy': '9–10',
                        happy: '7–8',
                        okay: '5–6',
                        tired: '3–4',
                        sad: '1–2',
                        missing: 'chưa có',
                    }
                    return (
                        <span key={face} className="inline-flex items-center gap-1">
                            <PixelFaceSvg face={face} size={16} />
                            {labels[face]}
                        </span>
                    )
                })}
            </div>

            {/* day detail panel */}
            {selected && (
                <DayDetail
                    date={selected}
                    point={selectedPoint}
                    onClose={() => setSelected(null)}
                />
            )}
        </section>
    )
}
