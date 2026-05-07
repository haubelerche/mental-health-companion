import { BookOpen, Check, Heart, Lock } from 'lucide-react'
import type { RewardStoreItem } from '../../services/rewardsService'
import { ApiRequestError } from '../../api/types'
import { useThemeContext } from '../../contexts/ThemeContext'

type Props = {
    item: RewardStoreItem
    balance: number
    owned: boolean
    onPurchase: (itemId: string) => Promise<void>
}

export default function KnowledgeCard({ item, balance, owned, onPurchase }: Props) {
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
        <div className={`relative flex flex-col gap-3 rounded-2xl border p-4 shadow-sm transition-all ${isDark ? 'border-theme-border/30 bg-theme-surface/40 hover:bg-theme-surface/60' : 'border-serene-border/40 bg-white/60 hover:bg-white'} overflow-hidden`}>
            {owned && (
                <div className="absolute right-0 top-0 rounded-bl-xl bg-theme-accent/20 px-3 py-1 backdrop-blur-sm">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-theme-accent">Đã mở khoá</span>
                </div>
            )}
            
            <div className="flex items-start gap-4">
                <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${isDark ? 'bg-theme-surface/80 text-theme-accent' : 'bg-serene-primary/10 text-serene-primary'}`}>
                    <BookOpen className="h-6 w-6" />
                </div>
                <div className="flex-1 pt-1">
                    <h3 className={`font-semibold ${isDark ? 'text-theme-text-primary' : 'text-serene-ink'}`}>{item.title}</h3>
                    {item.subtitle && (
                        <p className={`mt-1 text-xs leading-relaxed ${isDark ? 'text-theme-text-secondary' : 'text-serene-muted'}`}>
                            {item.subtitle}
                        </p>
                    )}
                </div>
            </div>

            <div className="mt-2 flex items-center justify-between border-t border-theme-border/20 pt-3">
                <div className={`flex items-center gap-1.5 text-sm font-bold ${isDark ? 'text-rose-300' : 'text-rose-500'}`}>
                    {item.price_hearts.toLocaleString('vi-VN')} <Heart className="h-4 w-4" />
                </div>
                
                {owned ? (
                    <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        <Check className="h-4 w-4" />
                        Đã sở hữu
                    </div>
                ) : (
                    <button
                        type="button"
                        disabled={disabled}
                        onClick={handleClick}
                        className={`flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-medium transition-all ${
                            disabled
                                ? 'cursor-not-allowed bg-theme-surface/50 text-theme-text-secondary opacity-60'
                                : 'bg-theme-accent text-white hover:bg-theme-accent/90 active:scale-95'
                        }`}
                        title={!canAfford ? 'Không đủ Tim' : !requirementsMet ? 'Chưa đủ điều kiện' : undefined}
                    >
                        {!requirementsMet ? <Lock className="h-3.5 w-3.5" /> : null}
                        <span>Mở khoá</span>
                    </button>
                )}
            </div>
        </div>
    )
}
