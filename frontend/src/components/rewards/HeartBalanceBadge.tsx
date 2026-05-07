import { Heart, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { rewardsService } from '../../services/rewardsService'

type Props = {
    /** Externally controlled balance (e.g. after a purchase). When provided, skips the fetch. */
    balance?: number
    className?: string
}

export default function HeartBalanceBadge({ balance: externalBalance, className = '' }: Props) {
    const [balance, setBalance] = useState<number | null>(externalBalance ?? null)

    useEffect(() => {
        if (externalBalance !== undefined) {
            setBalance(externalBalance)
            return
        }
        let cancelled = false
        rewardsService.getBalance().then((data) => {
            if (!cancelled) setBalance(data.balance)
        }).catch(() => {/* silent — badge is non-critical */})
        return () => { cancelled = true }
    }, [externalBalance])

    if (balance === null) return null

    return (
        <div className={`inline-flex items-center gap-1.5 rounded-full bg-theme-surface px-4 py-2 border border-theme-border shadow-sm ${className}`}>
            <Heart className="h-4 w-4 text-rose-500" aria-hidden />
            <span className="font-bold text-rose-500">{balance.toLocaleString('vi-VN')}</span>
        </div>
    )
}
