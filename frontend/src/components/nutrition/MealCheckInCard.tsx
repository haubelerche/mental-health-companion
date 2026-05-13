import { useState, useEffect } from 'react'
import { Coffee, Sun, Utensils, Send, CheckCircle2, Loader2, History } from 'lucide-react'
import { nutritionService, type MealSlot, type TodayCheckinsResponse } from '../../services/nutritionService'
import { toast } from 'react-toastify'
import Mascot from '../pixel/Mascot'
import MealHistoryModal from './MealHistoryModal'

const SLOT_CONFIG: Record<MealSlot, { label: string; icon: any; color: string }> = {
    breakfast: { label: 'Bữa sáng', icon: Coffee, color: 'text-amber-500' },
    lunch: { label: 'Bữa trưa', icon: Sun, color: 'text-orange-500' },
    dinner: { label: 'Bữa tối', icon: Utensils, color: 'text-indigo-500' },
}

export default function MealCheckInCard() {
    const [status, setStatus] = useState<TodayCheckinsResponse | null>(null)
    const [selectedSlot, setSelectedSlot] = useState<MealSlot | null>(null)
    const [itemsText, setItemsText] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [loading, setLoading] = useState(true)
    const [historyOpen, setHistoryOpen] = useState(false)

    useEffect(() => {
        loadStatus()
    }, [])

    async function loadStatus() {
        try {
            const data = await nutritionService.getTodayCheckins()
            setStatus(data)
        } catch (error) {
            console.error('Failed to load nutrition status', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        if (!selectedSlot || !itemsText.trim()) return

        setIsSubmitting(true)
        try {
            const res = await nutritionService.postMealCheckin({
                meal_slot: selectedSlot,
                items_text: itemsText.trim(),
            })

            if (res.reward.granted) {
                console.log(`Đã ghi nhận! Bạn nhận được ${res.reward.amount} Tim 🧡`)
            } else {
                console.log('Đã ghi nhận bữa ăn của bạn!')
            }

            setItemsText('')
            setSelectedSlot(null)
            await loadStatus()
        } catch (error) {
            toast.error('Ghi nhận thất bại. Vui lòng thử lại.')
        } finally {
            setIsSubmitting(false)
        }
    }

    if (loading) {
        return (
            <div className="flex h-48 items-center justify-center rounded-[28px] bg-theme-surface/50 backdrop-blur-xl">
                <Loader2 className="h-8 w-8 animate-spin text-theme-accent/50" />
            </div>
        )
    }

    const claimedSlots = new Set(status?.claimed_slots || [])

    return (
        <section className="rounded-[28px] bg-theme-surface/80 p-6 backdrop-blur-2xl lg:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-stretch">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-6">
                        <Mascot variant="eat" size="sm" decorative />
                        <div>
                            <p className="text-[10px] uppercase tracking-[0.3em] text-theme-text-secondary/60">Nhật ký ăn uống</p>
                            <h3 className="font-display text-2xl italic text-theme-text-primary">Hôm nay bạn ăn gì?</h3>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        {(Object.entries(SLOT_CONFIG) as [MealSlot, any][]).map(([slot, cfg]) => {
                            const isClaimed = claimedSlots.has(slot)
                            const isSelected = selectedSlot === slot
                            const Icon = cfg.icon

                            return (
                                <button
                                    key={slot}
                                    disabled={isClaimed}
                                    onClick={() => setSelectedSlot(slot)}
                                    className={`relative flex flex-col items-center gap-2 rounded-2xl border p-4 transition-all
                                        ${isClaimed 
                                            ? 'border-emerald-500/30 bg-emerald-500/5 cursor-default opacity-80' 
                                            : isSelected 
                                                ? 'border-theme-accent bg-theme-accent/10 shadow-sm ring-1 ring-theme-accent/20' 
                                                : 'border-theme-secondary/30 bg-theme-surface/50 hover:border-theme-accent/50'}
                                    `}
                                >
                                    <Icon className={`h-6 w-6 ${isClaimed ? 'text-emerald-500' : cfg.color}`} />
                                    <span className={`text-[11px] font-semibold ${isClaimed ? 'text-emerald-600' : 'text-theme-text-primary'}`}>
                                        {cfg.label}
                                    </span>
                                    {isClaimed && <CheckCircle2 className="absolute top-2 right-2 h-3.5 w-3.5 text-emerald-500" />}
                                </button>
                            )
                        })}
                    </div>
                </div>

                <div className="flex-1 lg:pl-8 lg:border-l border-theme-border/20 flex flex-col justify-center">
                    {selectedSlot && !claimedSlots.has(selectedSlot) ? (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="text-[11px] font-bold uppercase tracking-wider text-theme-text-secondary ml-1">
                                    Nội dung bữa {SLOT_CONFIG[selectedSlot].label.toLowerCase()}
                                </label>
                                <textarea
                                    autoFocus
                                    value={itemsText}
                                    onChange={(e) => setItemsText(e.target.value)}
                                    placeholder="Ví dụ: 1 bát yến mạch, 1 quả chuối và ly sữa hạt..."
                                    className="mt-2 w-full rounded-2xl border border-theme-secondary/30 bg-theme-surface/70 p-4 text-sm text-theme-text-primary placeholder-theme-text-secondary/40 outline-none focus:ring-1 focus:ring-theme-accent/30 min-h-[120px] resize-none"
                                    required
                                />
                            </div>
                            <div className="flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setSelectedSlot(null)
                                        setItemsText('')
                                    }}
                                    className="px-4 py-2 text-xs font-medium text-theme-text-secondary hover:text-theme-text-primary transition-colors"
                                >
                                    Hủy
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting || !itemsText.trim()}
                                    className="flex items-center gap-2 rounded-xl bg-theme-accent px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-theme-accent/20 transition hover:brightness-110 disabled:opacity-50"
                                >
                                    {isSubmitting ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <>
                                            Ghi nhận <Send className="h-3.5 w-3.5" />
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="py-6 text-center">
                            <div className="mx-auto max-w-[280px]">
                                {claimedSlots.size === 3 ? (
                                    <div className="space-y-2">
                                        <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-500 mb-2">
                                            <CheckCircle2 className="h-6 w-6" />
                                        </div>
                                        <p className="text-sm font-semibold text-theme-text-primary">Đã hoàn thành nhật ký!</p>
                                        <p className="text-xs text-theme-text-secondary leading-relaxed">
                                            Bạn đã ghi nhận đủ 3 bữa ăn hôm nay. Hãy duy trì thói quen ăn uống lành mạnh nhé.
                                        </p>
                                    </div>
                                ) : (
                                    <p className="text-sm text-theme-text-secondary italic leading-relaxed">
                                        Chọn một bữa ăn phía bên trái để bắt đầu ghi nhận nhật ký dinh dưỡng của bạn.
                                    </p>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="mt-4 flex justify-center">
                <button
                    onClick={() => setHistoryOpen(true)}
                    className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-theme-text-secondary/60 hover:text-theme-accent transition-colors cursor-pointer"
                >
                    <History className="h-3.5 w-3.5" /> Xem lịch sử ghi nhận
                </button>
            </div>

            <MealHistoryModal 
                isOpen={historyOpen} 
                onClose={() => setHistoryOpen(false)} 
            />
        </section>
    )
}
