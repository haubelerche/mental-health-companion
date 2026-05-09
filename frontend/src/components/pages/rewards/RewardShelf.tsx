import type { RewardShelf as RewardShelfType } from '../../../services/rewardsService'
import RewardCard from './RewardCard'

const SHELF_LABELS: Record<string, string> = {
    persona: 'Người đồng hành',
    knowledge: 'Tri thức của Người đồng hành',
    mood_room: 'Không gian',
    micro_style: 'Tính cách của Người đồng hành',
    badge: 'Huy hiệu',
    special: 'Đặc biệt',
}

type Props = {
    shelf: RewardShelfType
    balance: number
    ownedItemIds: Set<string>
    onPurchase: (itemId: string) => Promise<void>
}

export default function RewardShelf({ shelf, balance, ownedItemIds, onPurchase }: Props) {
    if (shelf.items.length === 0) return null

    return (
        <section className="mb-6 p-3 ">
            <h2 className="text-2xl  font-display font-semibold text-theme-text-secondary text-shadow-2xl mb-3">
                {SHELF_LABELS[shelf.shelf] ?? shelf.shelf}
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {shelf.items.map((item) => (
                    <RewardCard
                        key={item.item_id}
                        item={item}
                        balance={balance}
                        owned={ownedItemIds.has(item.item_id)}
                        onPurchase={onPurchase}
                    />
                ))}
            </div>
        </section>
    )
}
