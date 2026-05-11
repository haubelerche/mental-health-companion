import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { PersonaProgress } from '../../../services/rewardsService'
import { rewardsService } from '../../../services/rewardsService'
import { personasService } from '../../../services/personasService'
import { ApiRequestError } from '../../../api/types'
import { ROUTE_PATHS } from '../../../routes/paths'

import { toast } from 'react-toastify'

const FETCH_TIMEOUT_MS = 20_000

const PERSONA_ORDER = ['ban_than', 'nguoi_thay', 'cun', 'meo', 'crush'] as const

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
    let timeoutId: ReturnType<typeof setTimeout> | undefined
    const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = window.setTimeout(() => reject(new Error(`timeout:${label}`)), ms)
    })
    return Promise.race([promise, timeoutPromise]).finally(() => {
        if (timeoutId !== undefined) window.clearTimeout(timeoutId)
    }) as Promise<T>
}

const PERSONA_LABEL: Record<string, string> = {
    ban_than: 'Bạn Tốt',
    nguoi_thay: 'Người Thầy',
    cun: 'Cún',
    meo: 'Mèo',
    crush: 'Crush',
}

type Props = {
    onSelect?: (personaId: string) => void
}

export default function PersonaSelector({ onSelect }: Props) {
    const [progress, setProgress] = useState<PersonaProgress[]>([])
    const [activePersonaId, setActivePersonaId] = useState<string>('ban_than')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const selectablePersonas = useMemo(() => {
        const byId = new Map(progress.map((p) => [p.persona_id, p]))
        return PERSONA_ORDER.map((id) => byId.get(id)).filter((p): p is PersonaProgress => Boolean(p))
    }, [progress])

    useEffect(() => {
        let cancelled = false
        void (async () => {
            const [meRes, progRes] = await Promise.allSettled([
                withTimeout(personasService.getMe(), FETCH_TIMEOUT_MS, 'profile'),
                withTimeout(rewardsService.getPersonasProgress(), FETCH_TIMEOUT_MS, 'personas_progress'),
            ])
            if (cancelled) return
            if (meRes.status === 'rejected') {
                const reason = meRes.reason
                const isTimeout = reason instanceof Error && reason.message.startsWith('timeout:')
                setError(
                    isTimeout
                        ? 'Tải hồ sơ quá lâu. Kiểm tra mạng hoặc backend rồi thử lại.'
                        : 'Không tải được hồ sơ (auth/me).',
                )
                setLoading(false)
                return
            }
            if (progRes.status === 'rejected') {
                const reason = progRes.reason
                const isTimeout = reason instanceof Error && reason.message.startsWith('timeout:')
                setError(
                    isTimeout
                        ? 'Tải tiến độ nhân vật quá lâu. Thử lại sau.'
                        : 'Không tải được tiến độ nhân vật (rewards/personas/progress).',
                )
                setLoading(false)
                return
            }
            const me = meRes.value
            const prog = progRes.value
            setProgress(prog.personas)
            const sel = me.persona_id?.trim()
            setActivePersonaId(sel && sel.length > 0 ? sel : 'ban_than')
            setLoading(false)
        })()
        return () => {
            cancelled = true
        }
    }, [])

    async function handleSelect(personaId: string) {
        if (personaId === activePersonaId) return
        setError(null)

        const p = selectablePersonas.find(x => x.persona_id === personaId)
        if (p && !p.is_core && !p.unlocked) {
            toast.info('Nhân vật này chưa mở khoá. Hãy đến Cửa hàng Thưởng để mở nhé!')
   
            return
        }

        try {
            const res = await personasService.select(personaId)
            setActivePersonaId(res.persona_id || personaId)
            onSelect?.(personaId)
        } catch (err) {
            if (err instanceof ApiRequestError) setError(err.message)
            else setError('Không đổi được nhân vật lúc này.')
        }
    }

    if (loading) return <p className="text-sm text-theme-text-secondary">Đang tải nhân vật…</p>
    if (error) return <p className="text-sm text-red-500">{error}</p>

    const value =
        selectablePersonas.some((p) => p.persona_id === activePersonaId) ? activePersonaId : selectablePersonas[0]?.persona_id

    return (
        <div className="space-y-2">
            <label className="sr-only" htmlFor="persona-select">
                Chọn nhân vật
            </label>
            <select
                id="persona-select"
                value={value || 'ban_than'}
                onChange={(e) => void handleSelect(e.target.value)}
                className="w-full rounded-lg border border-theme-border/40 bg-theme-surface/60 px-3 py-2 text-sm text-theme-text-primary"
            >
                {selectablePersonas.map((p) => (
                    <option key={p.persona_id} value={p.persona_id}>
                        {PERSONA_LABEL[p.persona_id] ?? p.persona_id} {(!p.is_core && !p.unlocked) ? ' (🔒)' : ''}
                    </option>
                ))}
            </select>
            <p className="text-[11px] leading-snug text-theme-text-secondary">
                Cún, Mèo, Crush chỉ hiện sau khi bạn mở khoá trong{' '}
                <Link to={ROUTE_PATHS.rewards} className="font-medium text-theme-accent underline underline-offset-2">
                    Cửa hàng Thưởng
                </Link>
                .
            </p>
        </div>
    )
}
