import { RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import {
    dashboardService,
    type ReflectDashboardResponse,
    type ReflectRange,
} from '../../../services/dashboardService'
import { ChallengeCards } from '../../dashboard/ChallengeCards'
import { CopingEffectivenessPanel } from '../../dashboard/CopingEffectivenessPanel'
import { CurrentSnapshotHero } from '../../dashboard/CurrentSnapshotHero'
import { DataQualityBadge } from '../../dashboard/DataQualityBadge'
import { DataQualityNotice } from '../../dashboard/DataQualityNotice'
import { LifestyleRhythmPanel } from '../../dashboard/LifestyleRhythmPanel'
import { MoodTrendChart } from '../../dashboard/MoodTrendChart'
import { NextStepsPlan } from '../../dashboard/NextStepsPlan'
import { PatternGroupCards } from '../../dashboard/PatternGroupCards'
import { PixelMoodCalendar } from '../../dashboard/PixelMoodCalendar'
import { ScreeningPanel } from '../../dashboard/ScreeningPanel'
import { TriggerEmotionHeatmap } from '../../dashboard/TriggerEmotionHeatmap'
import { Skeleton } from './Skeleton'

const RANGE_OPTIONS: Array<{ value: ReflectRange; label: string }> = [
    { value: '7d', label: '7 ngày' },
    { value: '14d', label: '14 ngày' },
    { value: '30d', label: '30 ngày' },
]

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

export default function Reflect() {
    const { user } = useAuth()
    const [range, setRange] = useState<ReflectRange>('7d')
    const [dashboard, setDashboard] = useState<ReflectDashboardResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!user) {
            setLoading(false)
            return
        }

        let mounted = true
        const loadDashboard = async () => {
            setLoading(true)
            setError(null)
            try {
                const data = await dashboardService.getReflectDashboard(range)
                if (mounted) setDashboard(data)
            } catch {
                if (mounted) setError('Không tải được dữ liệu Nhìn lại. Vui lòng thử lại sau.')
            } finally {
                if (mounted) setLoading(false)
            }
        }

        loadDashboard()
        return () => {
            mounted = false
        }
    }, [range, user])

    return (
        <div className="relative min-h-screen overflow-x-hidden text-theme-text-primary">
            {/* subtle pixel grid background */}
            <div
                className="pointer-events-none fixed inset-0 opacity-[0.04]"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(77,99,89,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(77,99,89,.35) 1px, transparent 1px)',
                    backgroundSize: '22px 22px',
                }}
            />

            <main className="relative mx-auto flex flex-col gap-4 px-4 pb-16 pt-3 md:px-6">

                {/* ── Header ── */}
                <header className="rounded-2xl border border-theme-border bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-3">
                                <h1 className="font-display text-3xl leading-tight text-theme-text-primary md:text-4xl">
                                    Nhìn lại
                                </h1>
                                {dashboard && <DataQualityBadge dataQuality={dashboard.data_quality} />}
                            </div>
                            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-theme-text-secondary">
                                Một bản đồ nhỏ giúp bạn hiểu cảm xúc, giấc ngủ, ăn uống và những điều đang ảnh hưởng đến mình.
                            </p>
                        </div>

                        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center lg:flex-col lg:items-end">
                            <div className="inline-flex rounded-full border border-theme-border bg-theme-bg-secondary/80 p-1">
                                {RANGE_OPTIONS.map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setRange(option.value)}
                                        className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                                            range === option.value
                                                ? 'bg-theme-accent text-white shadow-sm'
                                                : 'text-theme-text-secondary hover:text-theme-text-primary'
                                        }`}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                            <p className="inline-flex items-center gap-2 text-xs text-theme-text-secondary">
                                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden />
                                Cập nhật: {dashboard ? formatUpdatedAt(dashboard.generated_at) : 'đang tải'}
                            </p>
                        </div>
                    </div>
                </header>

                {/* ── Error ── */}
                {error && (
                    <section className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100">
                        {error}
                    </section>
                )}

                {/* ── Loading skeleton ── */}
                {loading && !dashboard && <Skeleton />}

                {/* ── Dashboard sections ── */}
                {dashboard && (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        {/* 1. Tình hình hiện tại (Text) */}
                        <CurrentSnapshotHero dashboard={dashboard} />

                        {/* 4. Ngủ / ăn / năng lượng / kết nối (Text) */}
                        <LifestyleRhythmPanel dimensions={dashboard.dimensions} />

                        {/* 3. Nhịp cảm xúc & năng lượng (Chart) */}
                        <div className="md:col-span-2">
                            <MoodTrendChart
                                series={dashboard.mood_series}
                                enoughForTrend={dashboard.data_quality.enough_for_trend}
                            />
                        </div>

                        {/* 6. Khó khăn nổi bật (Text) */}
                        <ChallengeCards
                            summary={dashboard.summary}
                            checkins={dashboard.recent_checkins}
                            matrix={dashboard.trigger_emotion_matrix}
                        />

                        {/* 7. Dấu hiệu nên theo dõi thêm (Text) */}
                        <PatternGroupCards insights={dashboard.insights} />

                        {/* 2. Mood calendar (Chart) */}
                        <div className="md:col-span-2">
                            <PixelMoodCalendar series={dashboard.mood_series} range={dashboard.range} />
                        </div>

                        {/* 8. Sàng lọc (Full width) */}
                        {/* <div className="md:col-span-2">
                            <ScreeningPanel />
                        </div> */}

                        {/* 5. Trigger × Emotion heatmap (Chart) */}
                        <div className="md:col-span-2">
                            <TriggerEmotionHeatmap matrix={dashboard.trigger_emotion_matrix} />
                        </div>

                        {/* 9. Điều từng giúp (Text) */}
                        <CopingEffectivenessPanel insights={dashboard.insights} />

                        {/* 10. Một bước nhỏ hôm nay (Text) */}
                        <NextStepsPlan summary={dashboard.summary} />

                        {/* 11. Data quality notice */}
                        <div className="md:col-span-2">
                            <DataQualityNotice dataQuality={dashboard.data_quality} />
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}
