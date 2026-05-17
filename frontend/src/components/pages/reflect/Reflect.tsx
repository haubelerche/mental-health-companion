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
import { MoodByPeriodChart } from '../../dashboard/MoodByPeriodChart'
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

type DashboardTab = 'overview' | 'mood' | 'pattern' | 'lifestyle'

const TABS: Array<{ id: DashboardTab; label: string }> = [
    { id: 'overview', label: 'Tổng quan' },
    { id: 'mood', label: 'Tâm trạng' },
    { id: 'pattern', label: 'Khuynh hướng' },
    { id: 'lifestyle', label: 'Sinh hoạt' },
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

function TabBar({
    active,
    onChange,
}: {
    active: DashboardTab
    onChange: (tab: DashboardTab) => void
}) {
    return (
        <nav
            className="flex gap-1 rounded-2xl border border-theme-border bg-theme-surface p-1 shadow-md"
            role="tablist"
            aria-label="Dashboard sections"
        >
            {TABS.map((tab) => (
                <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={active === tab.id}
                    aria-controls={`tab-panel-${tab.id}`}
                    id={`tab-${tab.id}`}
                    onClick={() => onChange(tab.id)}
                    className={`flex flex-1 items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold transition-all duration-200 ${
                        active === tab.id
                            ? 'bg-theme-surface text-theme-accent shadow-sm ring-1 ring-theme-border/40'
                            : 'text-theme-text-secondary hover:bg-theme-surface/50 hover:text-theme-text-primary'
                    }`}
                >
                    {tab.label}
                </button>
            ))}
        </nav>
    )
}

function OverviewTab({ dashboard }: { dashboard: ReflectDashboardResponse }) {
    return (
        <div
            id="tab-panel-overview"
            role="tabpanel"
            aria-labelledby="tab-overview"
            className="flex flex-col gap-4"
        >
            <CurrentSnapshotHero dashboard={dashboard} />
            <DataQualityNotice dataQuality={dashboard.data_quality} />
        </div>
    )
}

function MoodTab({ dashboard }: { dashboard: ReflectDashboardResponse }) {
    return (
        <div
            id="tab-panel-mood"
            role="tabpanel"
            aria-labelledby="tab-mood"
            className="flex flex-col gap-4"
        >
            <PixelMoodCalendar series={dashboard.mood_series} range={dashboard.range} />
            <MoodTrendChart
                series={dashboard.mood_series}
                enoughForTrend={dashboard.data_quality.enough_for_trend}
            />
            <MoodByPeriodChart data={dashboard.mood_by_period} />
        </div>
    )
}

function PatternTab({ dashboard }: { dashboard: ReflectDashboardResponse }) {
    return (
        <div
            id="tab-panel-pattern"
            role="tabpanel"
            aria-labelledby="tab-pattern"
            className="flex flex-col gap-4"
        >
            <TriggerEmotionHeatmap matrix={dashboard.trigger_emotion_matrix} />
            <PatternGroupCards insights={dashboard.insights} />
            <ChallengeCards
                summary={dashboard.summary}
                checkins={dashboard.recent_checkins}
                matrix={dashboard.trigger_emotion_matrix}
            />
            <CopingEffectivenessPanel insights={dashboard.insights} />
        </div>
    )
}

function LifestyleTab({ dashboard }: { dashboard: ReflectDashboardResponse }) {
    return (
        <div
            id="tab-panel-lifestyle"
            role="tabpanel"
            aria-labelledby="tab-lifestyle"
            className="flex flex-col gap-4"
        >
            <LifestyleRhythmPanel dimensions={dashboard.dimensions} insights={dashboard.insights} />
            <ScreeningPanel />
            <NextStepsPlan summary={dashboard.summary} />
        </div>
    )
}

export default function Reflect() {
    const { user } = useAuth()
    const [range, setRange] = useState<ReflectRange>('7d')
    const [activeTab, setActiveTab] = useState<DashboardTab>('overview')
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
            <div
                className="pointer-events-none fixed inset-0 opacity-[0.04]"
                style={{
                    backgroundImage:
                        'linear-gradient(rgba(77,99,89,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(77,99,89,.35) 1px, transparent 1px)',
                    backgroundSize: '22px 22px',
                }}
            />

            <main className="relative mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 pb-16 pt-3 md:px-6">
                <header className="rounded-2xl border border-theme-border bg-theme-surface p-4 shadow-sm backdrop-blur-xl md:p-5">
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

                {error && (
                    <section className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100">
                        {error}
                    </section>
                )}

                {loading && !dashboard && <Skeleton />}

                {dashboard && (
                    <>
                        <TabBar active={activeTab} onChange={setActiveTab} />

                        {activeTab === 'overview' && <OverviewTab dashboard={dashboard} />}
                        {activeTab === 'mood' && <MoodTab dashboard={dashboard} />}
                        {activeTab === 'pattern' && <PatternTab dashboard={dashboard} />}
                        {activeTab === 'lifestyle' && <LifestyleTab dashboard={dashboard} />}
                    </>
                )}
            </main>
        </div>
    )
}
