import type { RewardShelf as RewardShelfType } from '../../../services/rewardsService'
import KnowledgeCard from './KnowledgeCard'
import bookIcon from '../../../assets/rewards/book1.gif'

type Props = {
    shelf: RewardShelfType
    balance: number
    ownedItemIds: Set<string>
    onPurchase: (itemId: string) => Promise<void>
}

export default function KnowledgeShelf({ shelf, balance, ownedItemIds, onPurchase }: Props) {
    if (shelf.items.length === 0) return null

    return (
        <section className="mb-6 p-3">
            <div className="mb-4 flex items-center gap-2">
                <img
                    src={bookIcon}
                    alt=""
                    className="h-12 w-12 shrink-0 object-contain [image-rendering:pixelated]"
                    aria-hidden="true"
                />
                <h2 className="text-2xl font-display font-semibold text-theme-text-primary text-shadow-2xl">
                    Tri thức của Người đồng hành
                </h2>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-2">
                {shelf.items.map((item) => (
                    <KnowledgeCard
                        key={item.item_id}
                        item={item}
                        balance={balance}
                        owned={ownedItemIds.has(item.item_id)}
                        onPurchase={onPurchase}
                        comingSoon
                    />
                ))}
            </div>
        </section>
    )
}
