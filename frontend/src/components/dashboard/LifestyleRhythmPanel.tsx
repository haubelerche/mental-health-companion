import { BedDouble, Salad, Zap, Users } from 'lucide-react'
import type { ReflectWellnessDimension } from '../../services/dashboardService'
import { useThemeContext } from '../../contexts/ThemeContext'

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
        fallback: 'Serene chưa có dữ liệu giấc ngủ. Check-in buổi tối giúp theo dõi thêm.',
    },
    body: {
        icon: Salad,
        label: 'Ăn uống & cơ thể',
        iconColor: 'text-emerald-500',
        fallback: 'Ghi nhận bữa ăn giúp Serene thấy mối liên hệ với năng lượng và mood của bạn.',
    },
    emotion: {
        icon: Zap,
        label: 'Năng lượng',
        iconColor: 'text-amber-400',
        fallback: 'Thêm mức năng lượng vào check-in để so sánh với trạng thái cảm xúc.',
    },
    connection: {
        icon: Users,
        label: 'Kết nối',
        iconColor: 'text-rose-400',
        fallback: 'Ghi chú về tương tác xã hội trong tuần sẽ giúp nhìn rõ hơn phần này.',
    },
    mindfulness: {
        icon: Zap,
        label: 'Thư giãn',
        iconColor: 'text-purple-400',
        fallback: 'Các bài tập thở và chánh niệm sẽ được tổng kết ở đây.',
    },
    growth: {
        icon: Users,
        label: 'Phát triển',
        iconColor: 'text-teal-400',
        fallback: 'Thêm ghi chú về học hỏi và thành tựu nhỏ để theo dõi phát triển cá nhân.',
    },
} as const

const PRIORITY_DIMS = ['sleep', 'body', 'emotion', 'connection'] as const

type LifestyleCard = {
    key: string
    icon: React.ComponentType<{ className?: string }>
    label: string
    iconColor: string
    status: StatusType
    explanation: string
    evidenceText: string
    suggestedAction: string | null
}

function buildCards(dimensions: ReflectWellnessDimension[]): LifestyleCard[] {
    const dimMap = new Map(dimensions.map((d) => [d.dimension, d]))
    return PRIORITY_DIMS.map((key) => {
        const dim = dimMap.get(key)
        const config = DIMENSION_CONFIG[key]
        return {
            key,
            icon: config.icon,
            label: dim?.label ?? config.label,
            iconColor: config.iconColor,
            status: dim?.status ?? 'unknown',
            explanation: dim?.explanation ?? config.fallback,
            evidenceText: dim?.evidence_text ?? 'Chưa có dữ liệu',
            suggestedAction: dim?.suggested_action ?? null,
        }
    })
}

function LifestyleCard({ card }: { card: LifestyleCard }) {
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    const statusCardBg = {
        unknown: isDark ? 'bg-gray-400/8' : 'bg-gray-50/80',
        limited_data: isDark ? 'bg-gray-400/8' : 'bg-gray-50/80',
        steady: isDark ? 'bg-emerald-400/8' : 'bg-emerald-50/80',
        needs_attention: isDark ? 'bg-amber-400/8' : 'bg-amber-50/80',
        improving: isDark ? 'bg-cyan-400/8' : 'bg-cyan-50/80',
    }

    const actionClass = isDark ? 'text-emerald-300' : 'text-emerald-700'
    const Icon = card.icon

    return (
        <div
            className={`rounded-2xl border border-theme-secondary/30 p-4 ${statusCardBg[card.status]} transition duration-200`}
        >
            <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 shrink-0 ${card.iconColor}`} aria-hidden />
                    <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-theme-text-tertiary">
                        {card.label}
                    </p>
                </div>
                <span
                    className={`inline-flex  items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold text-theme-text-secondary`}
                >
                    <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[card.status]}`} />
                    {STATUS_LABEL[card.status]}
                </span>
            </div>
            <p className="text-sm leading-relaxed text-theme-text-secondary">
                {card.explanation}
            </p>
            {card.suggestedAction && (
                <p className={`mt-2 text-xs font-medium ${actionClass}`}>
                    → {card.suggestedAction}
                </p>
            )}
        </div>
    )
}

export function LifestyleRhythmPanel({ dimensions }: Props) {
    const cards = buildCards(dimensions)

    return (
        <section className="rounded-2xl border border-theme-border bg-theme-surface/92 p-4 shadow-sm backdrop-blur-xl md:p-5">
            <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-theme-text-tertiary">Nhịp sinh hoạt</p>
                <h2 className="mt-1 text-xl font-semibold text-theme-text-primary">Ngủ, ăn, năng lượng & kết nối</h2>
                <p className="mt-1 text-sm leading-relaxed text-theme-text-secondary">
                    Các yếu tố sinh hoạt thường ảnh hưởng đến cảm xúc theo cách khó nhận ra ngay.
                </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
                {cards.map((card) => (
                    <LifestyleCard key={card.key} card={card} />
                ))}
            </div>
        </section>
    )
}
