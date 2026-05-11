import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'

type Props = {
    open: boolean
    onClose: () => void
}

const PHASES = [
    { label: 'Hít vào', seconds: 4 },
    { label: 'Giữ nhẹ', seconds: 4 },
    { label: 'Thở ra', seconds: 6 },
]
const MAX_CYCLES = 5

export function BreathingTimer({ open, onClose }: Props) {
    const [tick, setTick] = useState(0)
    const total = useMemo(() => PHASES.reduce((sum, p) => sum + p.seconds, 0), [])
    const maxTicks = total * MAX_CYCLES
    const completed = tick >= maxTicks

    useEffect(() => {
        if (!open) {
            setTick(0)
            return
        }
        if (completed) return
        const id = window.setInterval(() => setTick((v) => v + 1), 1000)
        return () => window.clearInterval(id)
    }, [completed, open])

    if (!open) return null

    const safeTick = Math.min(tick, Math.max(0, maxTicks - 1))
    const cycleTick = safeTick % total
    let cursor = 0
    const phase = PHASES.find((p) => {
        const active = cycleTick >= cursor && cycleTick < cursor + p.seconds
        cursor += p.seconds
        return active
    }) ?? PHASES[0]
    const remaining = completed ? 0 : phase.seconds - (cycleTick - (cursor - phase.seconds))

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
            <section className="w-full max-w-sm border border-[#8a6a3f]/60 bg-[#fff4dc] p-5 text-[#1a1008] shadow-[4px_4px_0_rgba(0,0,0,0.45)]">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold uppercase tracking-[0.18em]">Thở chậm</h2>
                    <button type="button" onClick={onClose} aria-label="Đóng" className="p-1 text-[#1a1008]/60 hover:text-[#1a1008]">
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="mt-6 flex flex-col items-center">
                    <div className="flex h-36 w-36 items-center justify-center rounded-full border border-[#1a1008]/20 bg-[#1a1008] text-[#fff4dc]">
                        <div className="text-center">
                            <div className="text-xl font-semibold">{completed ? 'Đã đủ 5 vòng' : phase.label}</div>
                            <div className="mt-1 text-4xl font-bold">{completed ? '✓' : remaining}</div>
                        </div>
                    </div>
                    <p className="mt-5 max-w-[260px] text-center text-sm leading-relaxed text-[#1a1008]/70">
                        {completed
                            ? 'Mình dừng bài thở ở đây. Bạn có thể quay lại cuộc trò chuyện khi sẵn sàng.'
                            : 'Bài thở này sẽ dừng sau 5 vòng. Chưa cần xử lý điều gì khác trong lúc này.'}
                    </p>
                    {completed && (
                        <button
                            type="button"
                            onClick={onClose}
                            className="mt-4 border border-[#1a1008]/25 bg-[#1a1008] px-4 py-2 text-sm font-semibold text-[#fff4dc] transition hover:bg-[#2c1a0d]"
                        >
                            Quay lại
                        </button>
                    )}
                </div>
            </section>
        </div>
    )
}
