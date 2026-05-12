import { useMemo, useState } from 'react'
import { X } from 'lucide-react'
import dungLuong from '../../assets/assistants/dung-luong.png'

type NutritionAssistantPopupProps = {
    defaultOpen?: boolean
    fact?: string | null
}

const FALLBACK_FACT = 'Một bữa ăn đều đặn, đủ chất và ít chế biến là nền tảng tốt cho sức khỏe thể chất lẫn tinh thần.'

export default function NutritionAssistantPopup({ defaultOpen = true, fact }: NutritionAssistantPopupProps) {
    const [open, setOpen] = useState(() => defaultOpen)
    const assistantLine = useMemo(() => {
        const value = typeof fact === 'string' ? fact.trim() : ''
        return value || FALLBACK_FACT
    }, [fact])

    const close = () => {
        setOpen(false)
    }

    if (!open) return null

    return (
        <aside className="fixed bottom-24 right-4 z-[62] w-[min(400px,calc(100vw-24px))] pt-32 text-[#3d2b1b] lg:bottom-8 lg:right-8">
            <img
                src={dungLuong}
                alt="Dung Luong"
                className="pointer-events-none absolute right-4 top-0 h-40 w-40 translate-y-5 object-contain"
                style={{ imageRendering: 'pixelated' }}
            />
            <div className="relative">
                <div className="relative z-20 ml-3 inline-flex border-[4px] border-[#5c3b24] bg-[#8a6040] px-6 py-2.5 text-lg font-black text-[#fff6d5] shadow-[4px_4px_0_rgba(55,38,20,0.28)]">
                    Dung Luong
                </div>
                <div className="relative z-10 -mt-1 border-4 border-[#6b4b2a] bg-[#f8e7b8] p-6 shadow-[0_7px_0_rgba(55,38,20,0.35)]">
                    <button
                        type="button"
                        onClick={close}
                        className="absolute right-4 top-4 inline-flex h-10 w-10 items-center justify-center border-2 border-[#6b4b2a] bg-[#fff6d5] text-[#5c3b24] transition hover:bg-[#f2d89e]"
                        aria-label="Đóng Dung Luong"
                    >
                        <X className="h-5 w-5" />
                    </button>
                    <p className="pr-12 text-base font-bold leading-relaxed text-[#5f5140]">{assistantLine}</p>
                </div>
            </div>
        </aside>
    )
}
