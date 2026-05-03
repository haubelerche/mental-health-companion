import { useEffect, useState } from 'react'
import type { RewardShelf as RewardShelfType } from '../../services/rewardsService'
import { rewardsService } from '../../services/rewardsService'
import RewardShelf from '../rewards/RewardShelf'
import HeartBalanceBadge from '../rewards/HeartBalanceBadge'
import { ApiRequestError } from '../../api/types'

export default function RewardsPage() {
    const [shelves, setShelves] = useState<RewardShelfType[]>([])
    const [balance, setBalance] = useState(0)
    const [ownedIds, setOwnedIds] = useState<Set<string>>(new Set())
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        Promise.all([rewardsService.getStore(), rewardsService.getInventory()])
            .then(([store, inv]) => {
                if (cancelled) return
                setShelves(store.shelves)
                setBalance(store.balance)
                setOwnedIds(new Set(inv.items.map((i) => i.item_id)))
            })
            .catch(() => { if (!cancelled) setError('Không tải được cửa hàng. Vui lòng thử lại.') })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [])

    async function handlePurchase(itemId: string) {
        try {
            const result = await rewardsService.purchase(itemId)
            setBalance(result.new_balance)
            setOwnedIds((prev) => new Set([...prev, result.item_id]))
        } catch (err) {
            if (err instanceof ApiRequestError) {
                if (err.code === 'already_owned') {
                    setOwnedIds((prev) => new Set([...prev, itemId]))
                }
            }
            throw err
        }
    }

    if (loading) {
        return (
            <div className="p-6 text-sm text-gray-400">Đang tải cửa hàng…</div>
        )
    }

    if (error) {
        return (
            <div className="p-6 text-sm text-red-500">{error}</div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto px-4 py-6">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-xl font-bold text-gray-900">Thưởng</h1>
                <HeartBalanceBadge balance={balance} />
            </div>

            {shelves.map((shelf) => (
                <RewardShelf
                    key={shelf.shelf}
                    shelf={shelf}
                    balance={balance}
                    ownedItemIds={ownedIds}
                    onPurchase={handlePurchase}
                />
            ))}

            {shelves.length === 0 && (
                <p className="text-sm text-gray-400">Cửa hàng chưa có mặt hàng nào.</p>
            )}
        </div>
    )
}
