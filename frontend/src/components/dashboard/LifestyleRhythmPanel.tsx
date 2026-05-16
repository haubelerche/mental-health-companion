import { BedDouble, PlusCircle, Salad, Users, Zap } from 'lucide-react'
import type { ComponentType } from 'react'
import type { ReflectWellnessDimension } from '../../services/dashboardService'

type Props = {
    dimensions: ReflectWellnessDimension[]
}

type StatusType = ReflectWellnessDimension['status']

const STATUS_DOT: Record<StatusType, string> = {
    unknown: 'bg-gray-300',
    limited_data: 'bg-gray-300',
    steady: 'bg-emerald-400',
    needs_attention: 'bg-amber-400',
    improving: 'bg-cyan-400',
}

const STATUS_LABEL: Record<StatusType, string> = {
    unknown: 'Chưa có dữ liệu',
    limited_data: 'Dữ liệu còn ít',
    steady: 'Ổn định',
    needs_attention: 'Cần chú ý thêm',
    improving: 'Đang cải thiện',
}

const DIMENSION_CONFIG = {
    sleep: {
        icon: BedDouble,
        label: 'Giấc ngủ',
        iconColor: 'text-indigo-400',
        dataNeededHint: 'Ghi số giờ ngủ trong check-in buổi tối để Serene thấy mối liên hệ với mood.',
    },
    body: {
        icon: Salad,
        label: 'Ăn uống & thể chất',
        iconColor: 'text-emerald-500',
        dataNeededHint: 'Log bữa ăn trong "Dinh dưỡng" để Serene theo dõi mối liên hệ với năng lượng.',
    },
    emotion: {
        icon: Zap,
        label: 'Cảm xúc & năng lượng',
        iconColor: 'text-amber-400',
        dataNeededHint: 'Thêm mức năng lượng vào check-in để phân biệt mood ổn với trạng thái còn sức hay kiệt sức.',
    },
    connection: {
        icon: Users,
        label: 'Kết nối',
        iconColor: 'text-rose-400',
        dataNeededHint: 'Nhắn ghi chú về tương tác xã hội trong tuần để Serene thấy tác động đến mood.',
    },
} as const

const PRIORITY_DIMS = ['sleep', 'body', 'emotion', 'connection'] as const

const STATUS_INSIGHT_BG: Record<string, string> = {
    steady: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-400/8 dark:border-emerald-400/20',
    improving: 'bg-cyan-50 border-cyan-200 dark:bg-cyan-400/8 dark:border-cyan-400/20',
    needs_attention: 'bg-amber-50 border-amber-200 dark:bg-amber-400/8 dark:border-amber-400/20',
}

function InsightCard({
    icon: Icon,
    label,
    iconColor,
    status,
    explanation,
    evidenceText,
    evidenceCount,
    suggestedAction,
}: {
    icon: ComponentType<{ className?: string }>
    label: string
    iconColor: string
    status: StatusType
    explanation: string
    evidenceText: string
    evidenceCount: number
    suggestedAction: string | null
}) {
    const bgClass = STATUS_INSIGHT_BG[status] ?? 'bg-theme-bg-secondary border-theme-border'
    return (
        <div className={`rounded-2xl border p-4 ${bgClass} transition duration-200`}>
            <div className="mb-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} aria-hidden />
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-theme-text-primary">
                        {label}
                    </p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-current/20 bg-white/60 px-2.5 py-0.5 text-[10px] font-semibold text-theme-text-secondary dark:bg-white/5">
                    <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
                    {STATUS_LABEL[status]}
                </span>
            </div>
            <p className="text-sm leading-relaxed text-theme-text-primary">{explanation}</p>
            {evidenceCount > 0 && (
                <p className="mt-2 text-xs text-theme-text-secondary">{evidenceText}</p>
            )}
            {suggestedAction && (
                <p className="mt-2 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                    {suggestedAction}
                </p>
            )}
        </div>
    )
}

function DataNeededCard({
    icon: Icon,
    label,
    iconColor,
    hint,
}: {
    icon: ComponentType<{ className?: string }>
    label: string
    iconColor: string
    hint: string
}) {
    return (
        <div className="rounded-2xl border border-dashed border-theme-border/70 bg-theme-bg-secondary/50 p-4 transition duration-200">
            <div className="mb-2 flex items-center gap-2">
                <Icon className={`h-4 w-4 shrink-0 ${iconColor} opacity-50`} aria-hidden />
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-theme-text-tertiary">
                    {label}
                </p>
                <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-theme-text-tertiary">
                    <PlusCircle className="h-3 w-3" aria-hidden />
                    Cần thêm dữ liệu
                </span>
            </div>
            <p className="text-sm leading-relaxed text-theme-text-secondary">{hint}</p>
        </div>
    )
}

export function LifestyleRhythmPanel({ dimensions }: Props) {
    const dimMap = new Map(dimensions.map((d) => [d.dimension, d]))

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Nhịp sinh hoạt</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Ngủ, ăn, năng lượng & kết nối</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Các yếu tố sinh hoạt thường ảnh hưởng đến cảm xúc theo cách khó nhận ra ngay.
                </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
                {PRIORITY_DIMS.map((key) => {
                    const dim = dimMap.get(key)
                    const config = DIMENSION_CONFIG[key]
                    const status = dim?.status ?? 'unknown'
                    const hasInsight = status === 'steady' || status === 'improving' || status === 'needs_attention'

                    if (!hasInsight || !dim?.explanation) {
                        return (
                            <DataNeededCard
                                key={key}
                                icon={config.icon}
                                label={config.label}
                                iconColor={config.iconColor}
                                hint={config.dataNeededHint}
                            />
                        )
                    }

                    return (
                        <InsightCard
                            key={key}
                            icon={config.icon}
                            label={dim.label ?? config.label}
                            iconColor={config.iconColor}
                            status={status}
                            explanation={dim.explanation}
                            evidenceText={dim.evidence_text ?? ''}
                            evidenceCount={dim.evidence_count ?? 0}
                            suggestedAction={dim.suggested_action ?? null}
                        />
                    )
                })}
            </div>
        </section>
    )
}
