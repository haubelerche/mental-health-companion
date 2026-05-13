import { useEffect, useState } from 'react'
import Modal from 'react-modal'
import { X, Coffee, Sun, Utensils } from 'lucide-react'
import { nutritionService, type MealHistoryItem, type MealSlot } from '../../services/nutritionService'
import Loading from '../ui/Loading'
import { parseTime } from '@/utils/parseTime'

type Props = {
    isOpen: boolean
    onClose: () => void
}

const SLOT_CONFIG: Record<MealSlot, { label: string; icon: any; color: string }> = {
    breakfast: { label: 'Bữa sáng', icon: Coffee, color: 'text-amber-600' },
    lunch: { label: 'Bữa trưa', icon: Sun, color: 'text-orange-600' },
    dinner: { label: 'Bữa tối', icon: Utensils, color: 'text-indigo-600' },
}

export default function MealHistoryModal({ isOpen, onClose }: Props) {
    const [history, setHistory] = useState<MealHistoryItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (typeof document !== 'undefined') {
            Modal.setAppElement('#root')
        }
    }, [])

    const fetchHistory = async () => {
        try {
            setLoading(true)
            const data = await nutritionService.getMealHistory()
            setHistory(data.checkins)
        } catch (err) {
            console.error('Failed to fetch meal history:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (isOpen) {
            fetchHistory()
        }
    }, [isOpen])

    const ui = {
        bg: 'bg-[#f8e7b8]',
        text: 'text-[#3d2b1b]',
        subtext: 'text-[#5f5140]',
        card: 'bg-[#fff6d5] border-2 border-[#6b4b2a]',
        headerBg: 'bg-[#8a6040]',
        headerText: 'text-[#fff6d5]',
    }

    return (
        <Modal
            isOpen={isOpen}
            onRequestClose={onClose}
            shouldCloseOnEsc
            shouldCloseOnOverlayClick
            contentLabel="Lịch sử bữa ăn"
            className="relative z-[81] mb-5 flex max-h-[80dvh] w-full max-w-2xl flex-col overflow-hidden border-4 border-[#6b4b2a] bg-[#f8e7b8] shadow-[0_7px_0_rgba(55,38,20,0.35)] outline-none"
            overlayClassName="fixed inset-0 z-[80] flex items-end justify-center sm:items-center bg-black/50 backdrop-blur-xs"
        >
            <div className={`flex items-center justify-between border-b-4 border-[#5c3b24] ${ui.headerBg} px-5 py-4 ${ui.headerText}`}>
                <div>
                    <p className="text-sm font-black uppercase tracking-[0.22em]">
                        Lịch sử bữa ăn
                    </p>
                </div>
                <button
                    type="button"
                    onClick={onClose}
                    className="border-2 border-[#6b4b2a] bg-[#fff6d5] text-[#5c3b24] p-1.5 hover:bg-[#f2d89e] transition-colors cursor-pointer"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>

            <div className="overflow-y-auto px-5 pb-8 pt-4">
                {loading ? (
                    <Loading />
                ) : history.length === 0 ? (
                    <div className="text-center py-10">
                        <div className="text-6xl mb-4 text-theme-accent/30">🍱</div>
                        <p className={ui.subtext}>Bạn chưa có lịch sử bữa ăn nào.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {history.map((item, idx) => {
                            const cfg = SLOT_CONFIG[item.meal_slot]
                            const Icon = cfg.icon
                            return (
                                <div
                                    key={`${item.meal_date}-${item.meal_slot}-${idx}`}
                                    className={`p-4 ${ui.card} shadow-[2px_2px_0_rgba(55,38,20,0.2)]`}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            <Icon className={`h-4 w-4 ${cfg.color}`} />
                                            <span className={`text-xs font-black uppercase tracking-wider ${ui.text}`}>
                                                {cfg.label}
                                            </span>
                                        </div>
                                        <span className={`text-[10px] font-bold ${ui.subtext}`}>
                                            {item.meal_date} {item.created_at && `• ${parseTime(item.created_at)}`}
                                        </span>
                                    </div>
                                    <p className={`text-xs font-bold ${ui.subtext} leading-relaxed bg-white/30 p-2 border border-[#6b4b2a]/10 rounded`}>
                                        {item.items_text}
                                    </p>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </Modal>
    )
}
