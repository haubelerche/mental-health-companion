import type { RewardShelf as RewardShelfType } from '../../../services/rewardsService'
import RewardCard from './RewardCard'
import yellowHeartIcon from '../../../assets/rewards/yellow-heart.gif'
import treeIcon from '../../../assets/rewards/tree2.gif'
import purpleHeartIcon from '../../../assets/rewards/purple-heart.gif'

const SHELF_LABELS: Record<string, string> = {
    persona: 'Người đồng hành',
    knowledge: 'Tri thức của Người đồng hành',
    mood_room: 'Không gian',
    micro_style: 'Tính cách của Người đồng hành',
    badge: 'Huy hiệu',
    special: 'Đặc biệt',
}

const SHELF_ICONS: Record<string, string> = {
    persona: yellowHeartIcon,
    mood_room: treeIcon,
    micro_style: purpleHeartIcon,
}

type Props = {
    shelf: RewardShelfType
    balance: number
    ownedItemIds: Set<string>
    onPurchase: (itemId: string) => Promise<void>
}

export default function RewardShelf({ shelf, balance, ownedItemIds, onPurchase }: Props) {
    if (shelf.items.length === 0) return null
    const shelfIcon = SHELF_ICONS[shelf.shelf]

    return (
        <section className="mb-6 p-3">
            <div className="mb-3 flex items-center gap-2">
                {shelfIcon && (
                    <img
                        src={shelfIcon}
                        alt=""
                        className="h-12 w-12 shrink-0 object-contain [image-rendering:pixelated]"
                        aria-hidden="true"
                    />
                )}
                <h2 className="font-display text-2xl font-semibold text-theme-text-secondary text-shadow-2xl">
                    {SHELF_LABELS[shelf.shelf] ?? shelf.shelf}
                </h2>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-3">
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
