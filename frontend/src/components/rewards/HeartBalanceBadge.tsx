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
        <span className={`inline-flex items-center gap-1 text-sm font-medium ${className}`}>
            <span aria-hidden="true">🌟</span>
            <span>{balance.toLocaleString('vi-VN')} Tim</span>
        </span>
    )
}
