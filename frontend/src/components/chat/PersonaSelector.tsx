import { useEffect, useState } from 'react'
import type { PersonaProgress } from '../../services/rewardsService'
import { rewardsService } from '../../services/rewardsService'
import { personasService } from '../../services/personasService'
import { ApiRequestError } from '../../api/types'

const PERSONA_DISPLAY: Record<string, { label: string; note: string }> = {
    ban_than: { label: 'Bạn Tốt', note: 'Luôn sẵn sàng' },
    nguoi_thay: { label: 'Người Thầy', note: 'Luôn sẵn sàng' },
    cun: { label: 'Cún', note: 'Người đồng hành vui vẻ' },
    meo: { label: 'Mèo', note: 'Người đồng hành độc lập' },
    crush: { label: 'Người đặc biệt', note: 'Người đồng hành thân thiết' },
}

type Props = {
    onSelect?: (personaId: string) => void
}

export default function PersonaSelector({ onSelect }: Props) {
    const [progress, setProgress] = useState<PersonaProgress[]>([])
    const [balance, setBalance] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        Promise.all([rewardsService.getPersonasProgress(), rewardsService.getBalance()])
            .then(([prog, bal]) => {
                if (cancelled) return
                setProgress(prog.personas)
                setBalance(bal.balance)
            })
            .catch(() => { if (!cancelled) setError('Không tải được danh sách nhân vật.') })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [])

    async function handleSelect(personaId: string) {
        try {
            await personasService.select(personaId)
            onSelect?.(personaId)
        } catch (err) {
            if (err instanceof ApiRequestError) {
                setError(err.message)
            }
        }
    }

    if (loading) return <p className="text-sm text-gray-400">Đang tải nhân vật…</p>
    if (error) return <p className="text-sm text-red-500">{error}</p>

    return (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {progress.map((p) => {
                const display = PERSONA_DISPLAY[p.persona_id] ?? { label: p.persona_id, note: '' }
                const affordable = balance >= p.price_hearts
                return (
                    <button
                        key={p.persona_id}
                        type="button"
                        onClick={() => p.unlocked && handleSelect(p.persona_id)}
                        disabled={!p.unlocked}
                        className="rounded-xl border p-3 text-left transition-colors
                            disabled:opacity-60 disabled:cursor-default
                            enabled:border-indigo-300 enabled:hover:bg-indigo-50"
                        title={p.unlocked ? undefined : `Mở khoá: ${p.price_hearts.toLocaleString('vi-VN')} Tim`}
                    >
                        <p className="text-sm font-semibold">{display.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{display.note}</p>
                        {!p.unlocked && (
                            <p className="text-xs text-indigo-500 mt-1">
                                🔒 {p.price_hearts.toLocaleString('vi-VN')} Tim
                                {!affordable && <span className="text-gray-400"> (chưa đủ)</span>}
                            </p>
                        )}
                    </button>
                )
            })}
        </div>
    )
}
