import { ApiRequestError } from '@/api/types'
import { useThemeContext } from '@/contexts/ThemeContext'
import type { RewardStoreItem } from '@/services/rewardsService'
import { Gift, Heart } from 'lucide-react'
import crushIcon from '../../../assets/rewards/crush.gif'
import cunIcon from '../../../assets/rewards/cun.gif'
import meoIcon from '../../../assets/assets_gif/meo-buon-ba.gif'


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

const PERSONA_ICON_BY_ID: Record<string, string> = {
    crush: crushIcon,
    cun: cunIcon,
    meo: meoIcon,
}

function normalizePersonaKey(item: RewardStoreItem): string {
    return [item.item_id, item.icon_key, item.title]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
}

function getPersonaIcon(item: RewardStoreItem): string | null {
    if (item.item_type !== 'persona') return null
    const key = normalizePersonaKey(item)
    if (key.includes('crush')) return PERSONA_ICON_BY_ID.crush
    if (key.includes('cun') || key.includes('cún')) return PERSONA_ICON_BY_ID.cun
    if (key.includes('meo') || key.includes('mèo')) return PERSONA_ICON_BY_ID.meo
    return null
}

export default function RewardCard({ item, balance, owned, onPurchase }: Props) {
    const canAfford = balance >= item.price_hearts
    const requirementsMet = !item.requirements || Object.keys(item.requirements).length === 0
    const disabled = owned || !canAfford || !requirementsMet
    const personaIcon = getPersonaIcon(item)
    const { effectiveTheme } = useThemeContext()
    const isDark = effectiveTheme === 'dark'

    async function handleClick() {
        if (disabled) return
        try {
            await onPurchase(item.item_id)
        } catch (err) {
            const code = err instanceof ApiRequestError? err.code : undefined
            if (code === 'insufficient_hearts' || code === 'requirements_not_met') return
        }
    }

    return (
        <div className={`relative flex flex-col gap-3 rounded-2xl border p-4 shadow-xl transition-all hover:-translate-y-1 hover:shadow-md border-theme-text-secondary bg-theme-surface`}>
            {owned && (
                <div className="absolute right-0 top-0 rounded-bl-xl bg-theme-accent/20 px-3 py-1 backdrop-blur-sm">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-theme-accent">Đã sở hữu</span>
                </div>
            )}
            
            <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${isDark ? 'bg-amber-500/10' : 'bg-amber-100'}`}>
                {personaIcon ? (
                    <img
                        src={personaIcon}
                        alt=""
                        className="h-12 w-12 object-contain [image-rendering:pixelated]"
                        aria-hidden="true"
                    />
                ) : (
                    <Gift className={`h-6 w-6 ${item.icon_key ? 'text-amber-500' : 'text-amber-500/50'}`} aria-hidden />
                )}
            </div>
            
            <div className="flex-1">
                <p className="font-semibold text-theme-text-primary text-base leading-tight">{sanitizeTitle(item.title)}</p>
                {item.subtitle && (
                    <p className="text-[13px] text-theme-text-secondary mt-1.5 leading-relaxed">{item.subtitle}</p>
                )}
            </div>
            
            <div className="mt-2 flex items-center justify-between border-t border-theme-border/20 pt-3">
                <p className={`text-sm font-bold flex items-center gap-1.5 ${isDark ? 'text-rose-400' : 'text-rose-500'}`}>
                    {item.price_hearts.toLocaleString('vi-VN')} <Heart className="h-4 w-4" />
                </p>
                
                {!owned && (
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
                        Mua
                    </button>
                )}
            </div>
        </div>
    )
}
