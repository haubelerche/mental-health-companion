import { ApiRequestError } from '@/api/types'
import { useThemeContext } from '@/contexts/ThemeContext'
import type { RewardStoreItem } from '@/services/rewardsService'
import { Gift, Heart, Lock, X } from 'lucide-react'
import { useState } from 'react'
import { createPortal } from 'react-dom'
import datAvatar from '../../../assets/assistants/dat-le.png'
import dungAvatar from '../../../assets/assistants/dung-luong.png'
import hauAvatar from '../../../assets/assistants/hau-luong.png'

type Props = {
    item: RewardStoreItem
    balance: number
    owned: boolean
    onPurchase: (itemId: string) => Promise<void>
    comingSoon?: boolean
}

type PersonaDetail = {
    avatar: string
    cardLabel: string
    status: string
    name: string
    job: string
    personality: string
    quote: string
    core: boolean
}

const PERSONA_DETAILS: Record<string, PersonaDetail> = {
    persona_dung_luong: {
        avatar: dungAvatar,
        cardLabel: 'Sinh Viên Năm Tám',
        status: 'Đang trực ở trang Dinh Dưỡng',
        name: 'Dung Luong',
        job: 'Sinh viên sắp ra trường',
        personality: 'Vui vẻ, thánh meme, sống tích cực, biết lắng nghe.',
        quote: 'Nhỡ sau này không rực rỡ thì saooo... Thôi kệ nó, đi ăn đã. Có thực mới vực được đạo.',
        core: true,
    },
    persona_dat_le: {
        avatar: datAvatar,
        cardLabel: 'Intern Mắt Thâm',
        status: 'Đang trực ở hệ thống Thông Báo',
        name: 'Dat Le',
        job: 'Intern lương ba cọc, không đồng',
        personality: 'Trông im im thì đang nghĩ về triết lý cuộc đời, hay động viên, truyền cảm hứng',
        quote: 'Cái gì khó quá thì mình vừa khóc, vừa làm. Cứ dũng cảm tiến tiếp thì cuộc đời rồi sẽ rực rỡ thôi...',
        core: true,
    },
    persona_hau_luong: {
        avatar: hauAvatar,
        cardLabel: 'Nhân viên Tâm huyết',
        status: 'Đang bị nhốt ở công ty',
        name: 'Hau Luong',
        job: 'Nhân viên văn phòng',
        personality: 'Gang-gang, mindset "kệ kệ - kệ đi" nên chữa được lo âu và overthinking',
        quote: 'Hau cần được quang hợp, hãy tích tim để mở khóa cho Hau ra khỏi đây.',
        core: false,
    },
}

function personaDetailFor(item: RewardStoreItem): PersonaDetail | null {
    return PERSONA_DETAILS[item.item_id] ?? null
}

export default function RewardCard({ item, balance, owned, onPurchase, comingSoon = false }: Props) {
    const [detailOpen, setDetailOpen] = useState(false)
    const [purchasing, setPurchasing] = useState(false)
    const personaDetail = personaDetailFor(item)
    const isCorePersona = Boolean(personaDetail?.core)
    const effectiveOwned = owned || isCorePersona
    const canAfford = balance >= item.price_hearts
    const requirementsMet = !item.requirements || Object.keys(item.requirements).length === 0
    const disabled = comingSoon || effectiveOwned || !canAfford || !requirementsMet || purchasing
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    async function handlePurchase() {
        if (disabled) return
        setPurchasing(true)
        try {
            await onPurchase(item.item_id)
        } catch (err) {
            const code = err instanceof ApiRequestError ? err.code : undefined
            if (code === 'insufficient_hearts' || code === 'requirements_not_met') return
        } finally {
            setPurchasing(false)
        }
    }

    const title = personaDetail?.cardLabel ?? item.title
    const subtitle = personaDetail?.status ?? item.subtitle

    const detailModal = detailOpen && personaDetail ? createPortal(
        <div
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 px-4 py-6"
            role="dialog"
            aria-modal="true"
            onClick={() => setDetailOpen(false)}
        >
            <div
                className="max-h-[calc(100dvh-3rem)] w-full max-w-md overflow-y-auto rounded-2xl border border-theme-border bg-theme-surface p-5 shadow-2xl"
                onClick={(event) => event.stopPropagation()}
            >
                <div className="mb-4 flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <img src={personaDetail.avatar} alt="" className="h-20 w-20 rounded-xl object-contain" aria-hidden="true" />
                        <div>
                            <p className="text-lg font-bold text-theme-text-primary">{personaDetail.cardLabel}</p>
                            <p className="text-sm text-theme-text-secondary">{personaDetail.status}</p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setDetailOpen(false)}
                        className="rounded-lg p-2 text-theme-text-secondary transition-colors hover:bg-theme-border/20 hover:text-theme-text-primary"
                        aria-label="Đóng"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
                <div className="space-y-3 text-sm leading-relaxed text-theme-text-primary">
                    <p>- Tên: {personaDetail.name}</p>
                    <p>- Nghề nghiệp: {personaDetail.job}</p>
                    <p>- Tính cách: {personaDetail.personality}</p>
                    <p>- Câu cửa miệng: {personaDetail.quote}</p>
                </div>
            </div>
        </div>,
        document.body,
    ) : null

    return (
        <>
            <div
                className={`relative flex min-h-[17rem] flex-col gap-3 rounded-2xl border p-4 shadow-xl transition-all ${
                    comingSoon
                        ? 'border-slate-200 bg-white text-slate-900'
                        : 'border-theme-text-secondary bg-theme-surface hover:-translate-y-1 hover:shadow-md'
                }`}
                onClick={() => !comingSoon && personaDetail && setDetailOpen(true)}
                role={!comingSoon && personaDetail ? 'button' : undefined}
                tabIndex={!comingSoon && personaDetail ? 0 : undefined}
                aria-disabled={comingSoon || undefined}
                onKeyDown={(event) => {
                    if (!comingSoon && personaDetail && (event.key === 'Enter' || event.key === ' ')) {
                        event.preventDefault()
                        setDetailOpen(true)
                    }
                }}
            >
                {comingSoon && (
                    <div className="absolute right-0 top-0 rounded-bl-xl bg-slate-100 px-3 py-1">
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-600">
                            <Lock className="h-3 w-3" aria-hidden />
                            Đang được phát triển
                        </span>
                    </div>
                )}

                {!comingSoon && effectiveOwned && (
                    <div className="absolute right-0 top-0 rounded-bl-xl bg-theme-accent/20 px-3 py-1 backdrop-blur-sm">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-theme-accent">
                            {isCorePersona ? 'Đang túc trực' : 'Đã giải cứu'}
                        </span>
                    </div>
                )}

                <div className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-xl ${comingSoon ? 'bg-slate-100 text-slate-500' : isDark ? 'bg-amber-500/10' : 'bg-amber-100'}`}>
                    {personaDetail ? (
                        <img src={personaDetail.avatar} alt="" className="h-16 w-16 object-contain" aria-hidden="true" />
                    ) : comingSoon ? (
                        <Lock className="h-7 w-7" aria-hidden />
                    ) : (
                        <Gift className={`h-6 w-6 ${item.icon_key ? 'text-amber-500' : 'text-amber-500/50'}`} aria-hidden />
                    )}
                </div>

                <div className="flex-1">
                    <p className={`text-base font-semibold leading-tight ${comingSoon ? 'text-slate-900' : 'text-theme-text-primary'}`}>{title}</p>
                    {subtitle && <p className={`mt-1.5 text-[13px] leading-relaxed ${comingSoon ? 'text-slate-600' : 'text-theme-text-secondary'}`}>{subtitle}</p>}
                    {comingSoon && (
                        <p className="mt-3 text-[12px] font-medium leading-relaxed text-slate-500">
                            Chức năng này đang được phát triển, chưa sẵn sàng để dùng.
                        </p>
                    )}
                    {personaDetail && (
                        <p className="mt-3 line-clamp-3 text-[12px] leading-relaxed text-theme-text-secondary">
                            {personaDetail.personality}
                        </p>
                    )}
                </div>

                <div className="mt-2 flex items-center justify-between border-t border-theme-border/20 pt-3">
                    {comingSoon ? (
                        <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600">
                            <Lock className="h-4 w-4" aria-hidden />
                            Chưa mở
                        </p>
                    ) : isCorePersona ? (
                        <p className="text-sm font-bold text-theme-accent">Đang túc trực</p>
                    ) : (
                        <p className={`flex items-center gap-1.5 text-sm font-bold ${isDark ? 'text-rose-400' : 'text-rose-500'}`}>
                            {item.price_hearts.toLocaleString('vi-VN')} <Heart className="h-4 w-4" />
                        </p>
                    )}

                    {!comingSoon && !effectiveOwned && (
                        <button
                            type="button"
                            disabled={disabled}
                            onClick={(event) => {
                                event.stopPropagation()
                                void handlePurchase()
                            }}
                            className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
                                disabled
                                    ? 'cursor-not-allowed bg-theme-surface/50 text-theme-text-secondary opacity-60'
                                    : 'bg-theme-accent text-white hover:bg-theme-accent/90 active:scale-95'
                            }`}
                            title={!canAfford ? 'Không đủ Tim' : !requirementsMet ? 'Chưa đủ điều kiện' : undefined}
                        >
                            Giải cứu
                        </button>
                    )}
                </div>
            </div>

            {detailModal}
        </>
    )
}
