import { Mountain, Moon, Coffee, Users, BookOpen, AlertCircle } from 'lucide-react'
import type {
    ReflectDashboardSummary,
    ReflectRecentCheckin,
    TriggerEmotionMatrixCell,
} from '../../services/dashboardService'
import PixelEmptyState from '../pixel/PixelEmptyState'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    summary: ReflectDashboardSummary
    checkins: ReflectRecentCheckin[]
    matrix: TriggerEmotionMatrixCell[]
}

type ChallengeCard = {
    id: string
    title: string
    appearances: number
    linkedEmotions: string[]
    reflection: string
    icon: React.ComponentType<{ className?: string }>
    iconColor: string
    bgColor: string
}

function topEmotionsForTrigger(trigger: string, matrix: TriggerEmotionMatrixCell[]): string[] {
    return matrix
        .filter((cell) => cell.trigger === trigger)
        .sort((a, b) => b.count - a.count)
        .slice(0, 3)
        .map((cell) => cell.emotion)
}

const REFLECTIONS: ((trigger: string, count: number, emotions: string[]) => string)[] = [
    (trigger, count, emotions) =>
        emotions.length
            ? `"${trigger}" xuất hiện ${count} lần và thường đi cùng ${emotions.slice(0, 2).join(' và ')}. Nghe như đây là một nguồn sức ép thật sự trong tuần.`
            : `"${trigger}" lặp lại ${count} lần. Serene đang theo dõi để xem có pattern không.`,
    (trigger, count) =>
        `Tuần này "${trigger}" xuất hiện ${count} lần — nhiều hơn một lần bình thường. Bạn không cần giải quyết hết, chỉ cần nhận ra là đủ.`,
    (trigger, count, emotions) =>
        emotions.length
            ? `Mỗi lần "${trigger}" xuất hiện thường đi cùng cảm giác ${emotions[0]}. Biết điều này có thể giúp bạn chuẩn bị hơn vào lần sau.`
            : `"${trigger}" đã được ghi nhận ${count} lần. Đây có thể là một yếu tố đáng để quan tâm.`,
]

export function ChallengeCards({ summary, checkins: _checkins, matrix }: Props) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const TRIGGER_ICONS: Record<string, { icon: React.ComponentType<{ className?: string }>; iconColor: string; bgColor: string }> = {
        default: { icon: AlertCircle, iconColor: 'text-amber-500', bgColor: isDark ? 'bg-amber-400/8 border-amber-200/60' : 'bg-amber-50/70 border-amber-200/60' },
        deadline: { icon: Mountain, iconColor: 'text-amber-500', bgColor: isDark ? 'bg-amber-400/8 border-amber-200/60' : 'bg-amber-50/70 border-amber-200/60' },
        học: { icon: Mountain, iconColor: 'text-amber-500', bgColor: isDark ? 'bg-amber-400/8 border-amber-200/60' : 'bg-amber-50/70 border-amber-200/60' },
        ngủ: { icon: Moon, iconColor: 'text-indigo-400', bgColor: isDark ? 'bg-indigo-400/8 border-indigo-200/60' : 'bg-indigo-50/70 border-indigo-200/60' },
        ăn: { icon: Coffee, iconColor: 'text-emerald-500', bgColor: isDark ? 'bg-emerald-400/8 border-emerald-200/60' : 'bg-emerald-50/70 border-emerald-200/60' },
        bữa: { icon: Coffee, iconColor: 'text-emerald-500', bgColor: isDark ? 'bg-emerald-400/8 border-emerald-200/60' : 'bg-emerald-50/70 border-emerald-200/60' },
        gia: { icon: Users, iconColor: 'text-rose-400', bgColor: isDark ? 'bg-rose-400/8 border-rose-200/60' : 'bg-rose-50/70 border-rose-200/60' },
        bạn: { icon: Users, iconColor: 'text-rose-400', bgColor: isDark ? 'bg-rose-400/8 border-rose-200/60' : 'bg-rose-50/70 border-rose-200/60' },
        việc: { icon: BookOpen, iconColor: 'text-purple-400', bgColor: isDark ? 'bg-purple-400/8 border-purple-200/60' : 'bg-purple-50/70 border-purple-200/60' },
        công: { icon: BookOpen, iconColor: 'text-purple-400', bgColor: isDark ? 'bg-purple-400/8 border-purple-200/60' : 'bg-purple-50/70 border-purple-200/60' },
    }

    function matchIcon(trigger: string) {
        const lower = trigger.toLowerCase()
        for (const [key, val] of Object.entries(TRIGGER_ICONS)) {
            if (key !== 'default' && lower.includes(key)) return val
        }
        return TRIGGER_ICONS.default
    }

    function buildChallengeCards(): ChallengeCard[] {
        return summary.top_triggers.slice(0, 4).map((item, idx) => {
            const emotions = topEmotionsForTrigger(item.label, matrix)
            const config = matchIcon(item.label)
            const reflection = REFLECTIONS[idx % REFLECTIONS.length](item.label, item.count, emotions)
            return {
                id: item.label,
                title: item.label,
                appearances: item.count,
                linkedEmotions: emotions,
                reflection,
                icon: config.icon,
                iconColor: config.iconColor,
                bgColor: config.bgColor,
            }
        })
    }

    const cards = buildChallengeCards()

    if (cards.length === 0) {
        return (
            <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
                <div className="mb-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Khó khăn nổi bật</p>
                    <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Điều đang gây khó cho bạn</h2>
                </div>
                <PixelEmptyState
                    mascot="idle"
                    title="Chưa có trigger nào được ghi nhận."
                    description="Khi check-in có ghi trigger, Serene sẽ tổng kết những gì đang xuất hiện nhiều nhất trong tuần."
                />
            </section>
        )
    }

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Khó khăn nổi bật</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Điều đang gây khó cho bạn</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Những trigger xuất hiện nhiều lần trong {summary.range_days} ngày qua.
                </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
                {cards.map((card) => {
                    const Icon = card.icon
                    return (
                        <article
                            key={card.id}
                            className={`rounded-2xl border p-4 ${card.bgColor}`}
                        >
                            <div className="mb-2 flex items-center gap-2">
                                <span className={`flex h-7 w-7 items-center justify-center rounded-xl bg-white/70 shadow-sm ${card.iconColor}`}>
                                    <Icon className="h-4 w-4" aria-hidden />
                                </span>
                                <div className="min-w-0">
                                    <h3 className="text-sm font-semibold text-theme-text-primary leading-snug break-words">
                                        {card.title}
                                    </h3>
                                    <p className="text-[11px] text-theme-text-tertiary">
                                        Xuất hiện {card.appearances} lần
                                    </p>
                                </div>
                            </div>

                            {card.linkedEmotions.length > 0 && (
                                <div className="mb-2 flex flex-wrap gap-1">
                                    {card.linkedEmotions.map((e) => (
                                        <span
                                            key={e}
                                            className="rounded-full bg-white/60 px-2 py-0.5 text-[11px] font-medium text-theme-text-secondary"
                                        >
                                            {e}
                                        </span>
                                    ))}
                                </div>
                            )}

                            <p className="text-sm leading-relaxed text-theme-text-secondary">
                                {card.reflection}
                            </p>
                        </article>
                    )
                })}
            </div>
        </section>
    )
}
