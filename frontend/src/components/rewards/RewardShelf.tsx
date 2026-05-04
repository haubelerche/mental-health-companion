import type { RewardShelf as RewardShelfType } from '../../services/rewardsService'
import RewardCard from './RewardCard'

const SHELF_LABELS: Record<string, string> = {
    persona: 'Người đồng hành',
    knowledge: 'Tri thức',
    mood_room: 'Không gian',
    micro_style: 'Phong cách',
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
        <section className="mb-6">
            <h2 className="text-base font-semibold text-gray-700 mb-3">
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
