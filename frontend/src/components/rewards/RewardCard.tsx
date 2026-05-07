import { Gift, Heart } from 'lucide-react'
import type { RewardStoreItem } from '../../services/rewardsService'
import { ApiRequestError } from '../../api/types'
import { useThemeContext } from '@/contexts/ThemeContext'

type Props = {
    item: RewardStoreItem
    balance: number
    owned: boolean
    onPurchase: (itemId: string) => Promise<void>
}

const FORBIDDEN_CRUSH_COPY = ['người yêu AI', 'bạn trai', 'bạn gái', 'tình yêu thật']

function sanitizeTitle(title: string): string {
    for (const phrase of FORBIDDEN_CRUSH_COPY) {
        if (title.toLowerCase().includes(phrase.toLowerCase())) {
            return title.replace(new RegExp(phrase, 'gi'), 'người đồng hành')
        }
    }
    return title
}

export default function RewardCard({ item, balance, owned, onPurchase }: Props) {
    const canAfford = balance >= item.price_hearts
    const requirementsMet = !item.requirements || Object.keys(item.requirements).length === 0
    const disabled = owned || !canAfford || !requirementsMet
        const { effectiveTheme } = useThemeContext()
        const isDark = effectiveTheme === 'dark'

    async function handleClick() {
        if (disabled) return
        try {
            await onPurchase(item.item_id)
        } catch (err) {
            const code = err instanceof ApiRequestError ? err.code : undefined
            if (code === 'insufficient_hearts' || code === 'requirements_not_met') return
        }
    }

    return (
        <div className="rounded-xl border border-theme-surface/20 bg-theme-surface/60 p-4 flex flex-col gap-2 shadow-sm">
            {item.icon_key ? (
                <Gift className="h-7 w-7 text-amber-500/90" aria-hidden />
            ) : null}
            <p className="font-semibold text-theme-text-primary text-sm">{sanitizeTitle(item.title)}</p>
            {item.subtitle && (
                <p className="text-xs text-theme-text-secondary">{item.subtitle}</p>
            )}
            <p className={`text-xs font-medium mt-auto flex items-center gap-1 ${isDark ? 'text-rose-300' : 'text-rose-500'}`}>
                {item.price_hearts.toLocaleString('vi-VN')} <Heart className="h-4 w-4" />
            </p>
            {owned ? (
                <span className="text-xs text-green-600 font-medium">Đã sở hữu</span>
            ) : (
                <button
                    type="button"
                    disabled={disabled}
                    onClick={handleClick}
                    className="mt-1 w-full rounded-lg py-1.5 text-xs font-medium transition-colors
                        disabled:opacity-40 disabled:cursor-not-allowed
                        enabled:bg-indigo-600 enabled:text-white enabled:hover:bg-indigo-700"
                    title={!canAfford ? 'Không đủ Tim' : !requirementsMet ? 'Chưa đủ điều kiện' : undefined}
                >
                    Mua
                </button>
            )}
        </div>
    )
}
