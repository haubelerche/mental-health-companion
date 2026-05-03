import type { RewardStoreItem } from '../../services/rewardsService'
import { ApiRequestError } from '../../api/types'

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
        <div className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-2 shadow-sm">
            {item.icon_key && (
                <span className="text-2xl" aria-hidden="true">{item.icon_key}</span>
            )}
            <p className="font-semibold text-gray-900 text-sm">{sanitizeTitle(item.title)}</p>
            {item.subtitle && (
                <p className="text-xs text-gray-500">{item.subtitle}</p>
            )}
            <p className="text-xs font-medium text-indigo-600 mt-auto">
                {item.price_hearts.toLocaleString('vi-VN')} Tim
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
