import { Activity, BedDouble, Users, Zap } from 'lucide-react'
import type { ComponentType } from 'react'
import type { ReflectInsight, ReflectWellnessDimension } from '../../services/dashboardService'

type Props = {
    dimensions: ReflectWellnessDimension[]
    insights?: ReflectInsight[]
}

type DimKey = 'sleep' | 'nutrition' | 'emotion' | 'connection' | 'body'
type StatusType = ReflectWellnessDimension['status']

const STATUS_LABEL: Record<StatusType, string> = {
    unknown: 'Chưa đủ dữ liệu',
    limited_data: 'Dữ liệu còn ít',
    steady: 'Khá đều',
    needs_attention: 'Cần theo dõi thêm',
    improving: 'Đang tốt lên',
}

const STATUS_BADGE: Record<StatusType, string> = {
    unknown: 'text-theme-text-tertiary bg-theme-bg-secondary border-theme-border/60',
    limited_data: 'text-theme-text-secondary bg-theme-bg-secondary border-theme-border/60',
    steady: 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-300 dark:bg-emerald-400/10 dark:border-emerald-400/20',
    improving: 'text-cyan-700 bg-cyan-50 border-cyan-200 dark:text-cyan-300 dark:bg-cyan-400/10 dark:border-cyan-400/20',
    needs_attention: 'text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-300 dark:bg-amber-400/10 dark:border-amber-400/20',
}

const CARD_BG: Record<StatusType, string> = {
    unknown: 'bg-theme-bg-secondary/40 border-dashed border-theme-border/60',
    limited_data: 'bg-theme-bg-secondary/40 border-dashed border-theme-border/60',
    steady: 'bg-emerald-50/50 border-emerald-100 dark:bg-emerald-400/5 dark:border-emerald-400/15',
    improving: 'bg-cyan-50/50 border-cyan-100 dark:bg-cyan-400/5 dark:border-cyan-400/15',
    needs_attention: 'bg-amber-50/50 border-amber-100 dark:bg-amber-400/5 dark:border-amber-400/15',
}

type DimConfig = {
    icon: ComponentType<{ className?: string }>
    label: string
    iconColor: string
    evidenceUnit: string
    missingWhenEmpty: string
    missingWhenHasData: string
    fallbackExplanation: string
    fallbackAction: string
}

const DIMENSION_CONFIG: Record<DimKey, DimConfig> = {
    sleep: {
        icon: BedDouble,
        label: 'Giấc ngủ',
        iconColor: 'text-indigo-400',
        evidenceUnit: 'ngày có dữ liệu giấc ngủ',
        missingWhenEmpty: 'giờ ngủ, giờ dậy, chất lượng ngủ',
        missingWhenHasData: 'chất lượng ngủ từng đêm',
        fallbackExplanation:
            'Serene chưa thấy giờ đi ngủ hoặc giờ thức dậy trong các ghi nhận gần đây, nên chưa thể phân tích giấc ngủ ảnh hưởng thế nào đến tâm trạng của bạn.',
        fallbackAction: 'ghi lại giờ đi ngủ trước khi ngủ',
    },
    body: {
        icon: Activity,
        label: 'Hành động tự chăm sóc',
        iconColor: 'text-emerald-500',
        evidenceUnit: 'lần thử hành động nhỏ',
        missingWhenEmpty: 'hành động tự ổn định, mức năng lượng trong ngày',
        missingWhenHasData: 'hành động nào thật sự giúp bạn nhẹ nhất',
        fallbackExplanation:
            'Serene chưa có đủ thông tin về các hành động tự ổn định của bạn. Mỗi lần thử một hành động nhỏ, bạn đang giúp Serene hiểu điều gì thật sự có tác dụng.',
        fallbackAction: 'thử một hành động nhỏ tự ổn định hôm nay',
    },
    nutrition: {
        icon: Activity,
        label: 'Ăn uống và năng lượng',
        iconColor: 'text-lime-500',
        evidenceUnit: 'bữa ăn được ghi',
        missingWhenEmpty: 'bữa sáng, bữa trưa, bữa tối',
        missingWhenHasData: 'món ăn cụ thể và cảm giác sau bữa ăn',
        fallbackExplanation:
            'Serene chưa có đủ log bữa ăn để xem protein, chất xơ, đường hoặc caffeine đang ảnh hưởng đến năng lượng của bạn ra sao.',
        fallbackAction: 'ghi bữa gần nhất, chỉ cần tên món và cảm giác sau bữa ăn',
    },
    emotion: {
        icon: Zap,
        label: 'Cảm xúc',
        iconColor: 'text-amber-400',
        evidenceUnit: 'ngày có ghi nhận',
        missingWhenEmpty: 'dữ liệu theo buổi sáng, chiều, tối',
        missingWhenHasData: 'sáng · chiều · tối',
        fallbackExplanation:
            'Serene chưa có ghi nhận cảm xúc theo buổi, nên chưa thể thấy lúc nào trong ngày bạn thường dễ tụt nhất.',
        fallbackAction: 'thêm một ghi nhận ngắn vào buổi tối',
    },
    connection: {
        icon: Users,
        label: 'Kết nối',
        iconColor: 'text-rose-400',
        evidenceUnit: 'phiên trò chuyện',
        missingWhenEmpty: 'tương tác ngoài ứng dụng, người bạn tin tưởng',
        missingWhenHasData: 'người bạn có thể tin tưởng ngoài ứng dụng',
        fallbackExplanation:
            'Serene chưa có đủ dữ liệu về mức độ kết nối của bạn trong giai đoạn này.',
        fallbackAction: 'nhắn một câu rất ngắn cho một người an toàn',
    },
}

const PRIORITY_DIMS: DimKey[] = ['sleep', 'nutrition', 'emotion', 'connection', 'body']

function hasData(status: StatusType): boolean {
    return status === 'steady' || status === 'improving' || status === 'needs_attention'
}

function confidenceLabel(dims: ReflectWellnessDimension[]): string {
    const count = dims.filter((d) => hasData(d.status)).length
    if (count >= 3) return 'Cao'
    if (count >= 2) return 'Trung bình'
    return 'Thấp'
}

function buildEvidenceChips(dimMap: Map<string, ReflectWellnessDimension>): string[] {
    const chips: string[] = []

    const emotion = dimMap.get('emotion')
    if (emotion && hasData(emotion.status) && emotion.evidence_count > 0) {
        chips.push(`${emotion.evidence_count} ngày ghi nhận cảm xúc`)
    }

    const connection = dimMap.get('connection')
    if (connection && hasData(connection.status) && connection.evidence_count > 0) {
        chips.push(`${connection.evidence_count} phiên trò chuyện`)
    }

    const sleep = dimMap.get('sleep')
    if (!sleep || !hasData(sleep.status)) {
        chips.push('chưa có giờ ngủ')
    } else if (sleep.evidence_count > 0) {
        chips.push(`${sleep.evidence_count} ngày có dữ liệu giấc ngủ`)
    }

    const body = dimMap.get('body')
    if (body && hasData(body.status) && body.evidence_count > 0) {
        chips.push(`${body.evidence_count} lần thử hành động nhỏ`)
    }

    return chips.slice(0, 4)
}

function heroSummary(allDims: ReflectWellnessDimension[]): string {
    const needsAttn = allDims.find((d) => d.status === 'needs_attention')
    if (needsAttn?.explanation) return needsAttn.explanation

    const improving = allDims.find((d) => d.status === 'improving')
    if (improving?.explanation) return improving.explanation

    const steady = allDims.find((d) => d.status === 'steady')
    if (steady?.explanation) return steady.explanation

    const limited = allDims.find((d) => d.status === 'limited_data' && d.explanation)
    if (limited?.explanation) return limited.explanation

    return 'Serene chưa có đủ dữ liệu sinh hoạt để rút ra điều đáng chú ý. Bạn có thể ghi nhận thêm giờ ngủ, cảm xúc theo buổi, và trò chuyện nhỏ để Serene thấy rõ hơn.'
}

function HeroCard({
    dimMap,
    allDims,
}: {
    dimMap: Map<string, ReflectWellnessDimension>
    allDims: ReflectWellnessDimension[]
}) {
    const summary = heroSummary(allDims)
    const chips = buildEvidenceChips(dimMap)
    const confidence = confidenceLabel(allDims)

    return (
        <div className="rounded-2xl border border-theme-border bg-theme-bg-secondary/60 p-4 md:p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-theme-text-tertiary">
                Điều đáng chú ý nhất
            </p>
            <p className="mt-2 text-sm leading-relaxed text-theme-text-primary">{summary}</p>
            {chips.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                    {chips.map((chip) => (
                        <span
                            key={chip}
                            className="inline-flex items-center rounded-full bg-theme-surface px-3 py-1 text-xs text-theme-text-secondary ring-1 ring-theme-border"
                        >
                            {chip}
                        </span>
                    ))}
                </div>
            )}
            <p className="mt-3 text-xs text-theme-text-tertiary">
                Mức tin cậy:{' '}
                <span className="font-semibold text-theme-text-secondary">{confidence}</span>
            </p>
        </div>
    )
}

function LifestyleCard({
    dimKey,
    dim,
}: {
    dimKey: DimKey
    dim: ReflectWellnessDimension | undefined
}) {
    const config = DIMENSION_CONFIG[dimKey]
    const Icon = config.icon
    const displayLabel = dimKey === 'body' ? 'Hành động tự chăm sóc' : config.label
    const status: StatusType = dim?.status ?? 'unknown'
    const isDataReady = hasData(status)

    const explanation =
        dim?.explanation && dim.explanation.trim() ? dim.explanation : config.fallbackExplanation

    const evidenceText =
        isDataReady && dim && dim.evidence_count > 0
            ? `${dim.evidence_count} ${config.evidenceUnit}`
            : null

    const missingText = isDataReady ? config.missingWhenHasData : config.missingWhenEmpty

    const action = dim?.suggested_action ?? config.fallbackAction

    return (
        <div className={`rounded-2xl border p-4 transition duration-200 ${CARD_BG[status]}`}>
            <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                    <Icon
                        className={`h-4 w-4 shrink-0 ${config.iconColor} ${!isDataReady ? 'opacity-50' : ''}`}
                        aria-hidden
                    />
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-theme-text-primary">
                        {displayLabel}
                    </p>
                </div>
                <span
                    className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${STATUS_BADGE[status]}`}
                >
                    {STATUS_LABEL[status]}
                </span>
            </div>

            <p className="text-sm leading-relaxed text-theme-text-primary">{explanation}</p>

            {evidenceText && (
                <p className="mt-2 text-xs text-theme-text-secondary">
                    Dựa trên: {evidenceText}
                </p>
            )}

            <p className="mt-1.5 text-xs text-theme-text-tertiary">Còn thiếu: {missingText}</p>

            <div className="mt-3">
                <span className="inline-flex rounded-full bg-theme-surface px-3 py-1.5 text-xs font-medium text-theme-text-secondary ring-1 ring-theme-border">
                    Hôm nay thử: {action}
                </span>
            </div>
        </div>
    )
}

export function LifestyleRhythmPanel({ dimensions, insights = [] }: Props) {
    const nutritionInsight = insights.find((insight) => insight.category === 'nutrition' || insight.hypothesis_type === 'nutrition')
    const sleepInsight = insights.find((insight) => insight.category === 'sleep' || insight.hypothesis_type === 'sleep')
    const emotionInsight = insights.find((insight) => insight.category === 'daily_mood' || insight.category === 'emotion' || insight.hypothesis_type === 'daily_mood')
    const connectionInsight = insights.find((insight) => insight.category === 'real_world_connection' || insight.hypothesis_type === 'real_world_connection')
    const selfCareInsight = insights.find((insight) => insight.category === 'self_care_action' || insight.hypothesis_type === 'self_care_action')
    const enrichedDimensions = [...dimensions]

    const upsertInsightDimension = (
        insight: ReflectInsight | undefined,
        dimension: ReflectWellnessDimension['dimension'],
        label: string,
        evidenceUnit: string,
    ) => {
        if (!insight) return
        const status: StatusType = insight.severity_label.includes('chăm') || insight.severity_label.includes('theo dõi') ? 'needs_attention' : 'steady'
        const nextDimension: ReflectWellnessDimension = {
            dimension,
            label,
            status,
            score: null,
            explanation: insight.interpretation || insight.user_safe_summary,
            evidence_count: insight.evidence_count,
            suggested_action: insight.recommended_actions?.[0] || insight.suggested_action || null,
            evidence_text: `${insight.evidence_count} ${evidenceUnit}`,
        }
        const existingIndex = enrichedDimensions.findIndex((dim) => dim.dimension === dimension)
        if (existingIndex >= 0) {
            enrichedDimensions[existingIndex] = nextDimension
        } else {
            enrichedDimensions.push(nextDimension)
        }
    }

    upsertInsightDimension(sleepInsight, 'sleep', 'Giấc ngủ', 'ghi nhận giấc ngủ')
    upsertInsightDimension(nutritionInsight, 'nutrition', 'Ăn uống và năng lượng', 'bữa ăn được ghi')
    upsertInsightDimension(emotionInsight, 'emotion', 'Cảm xúc', 'ghi nhận cảm xúc')
    upsertInsightDimension(connectionInsight, 'connection', 'Kết nối ngoài đời', 'phiên trò chuyện')
    upsertInsightDimension(selfCareInsight, 'body', 'Hành động tự chăm sóc', 'ghi nhận hành động')

    const dimMap = new Map(enrichedDimensions.map((d) => [d.dimension, d]))

    return (
        <section className="rounded-2xl border border-theme-border/70 bg-theme-surface p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">
                    Nhịp sinh hoạt
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-theme-text-secondary">
                    Giấc ngủ, ăn uống, năng lượng và kết nối thường ảnh hưởng đến cảm xúc theo cách âm thầm.
                </p>
            </div>

            <HeroCard dimMap={dimMap} allDims={enrichedDimensions} />

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {PRIORITY_DIMS.map((key) => (
                    <LifestyleCard key={key} dimKey={key} dim={dimMap.get(key)} />
                ))}
            </div>
        </section>
    )
}
