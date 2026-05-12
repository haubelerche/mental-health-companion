import { useEffect, useState } from 'react'
import type { RewardShelf as RewardShelfType } from '../../../services/rewardsService'
import { rewardsService } from '../../../services/rewardsService'
import RewardShelf from '../rewards/RewardShelf'
import KnowledgeShelf from '../rewards/KnowledgeShelf'
import HeartBalanceBadge from '../rewards/HeartBalanceBadge'
import { ApiRequestError } from '../../../api/types'
import Loading from '../../ui/Loading'
import Mascot from '../../pixel/Mascot'
import PixelEmptyState from '../../pixel/PixelEmptyState'
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
        return <Loading text='Đang tải cửa hàng...' />
    }

    if (error) {
        return (
            <div className="p-6 text-sm text-red-500">{error}</div>
        )
    }

    return (
        <div className="relative min-h-screen text-theme-text-primary">
            <div className="mx-auto max-w-5xl px-4 py-6 md:py-8">
                <div className="rounded-[2.5rem] bg-theme-surface/85 backdrop-blur-xs p-6 md:p-8">
                    <div className="mb-6 flex items-center justify-between gap-4">
                        <Mascot variant="main" size="lg" decorative />
                        <h1 className="font-display text-center text-3xl font-bold text-theme-text-primary text-shadow-2xl">Cửa hàng vật phẩm</h1>
                        <HeartBalanceBadge balance={balance} />
                    </div>

            {shelves.map((shelf) => {
                if (shelf.shelf === 'knowledge') {
                    return (
                        <div key={shelf.shelf} data-tour-id="knowledge-card">
                        <KnowledgeShelf
                            shelf={shelf}
                            balance={balance}
                            ownedItemIds={ownedIds}
                            onPurchase={handlePurchase}
                        />
                        </div>
                    )
                }
                return (
                    <RewardShelf
                        key={shelf.shelf}
                        shelf={shelf}
                        balance={balance}
                        ownedItemIds={ownedIds}
                        onPurchase={handlePurchase}
                    />
                )
            })}

            {shelves.length === 0 && (
                <PixelEmptyState
                    mascot="rock"
                    title="Cửa hàng chưa có mặt hàng nào"
                    description="Khi backend mở catalog mới, các vật phẩm sẽ xuất hiện tại đây."
                />
            )}
                </div>
            </div>
        </div>
    )
}
