import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { PersonaProgress } from '../../services/rewardsService'
import { rewardsService } from '../../services/rewardsService'
import { personasService } from '../../services/personasService'
import { ApiRequestError } from '../../api/types'
import { ROUTE_PATHS } from '../../routes/paths'

const PERSONA_ORDER = ['ban_than', 'nguoi_thay', 'cun', 'meo', 'crush'] as const

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
        return PERSONA_ORDER.map((id) => byId.get(id)).filter(
            (p): p is PersonaProgress => Boolean(p && (p.is_core || p.unlocked)),
        )
    }, [progress])

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setError(null)
        Promise.all([personasService.getMe(), rewardsService.getPersonasProgress()])
            .then(([me, prog]) => {
                if (cancelled) return
                setProgress(prog.personas)
                const sel = me.persona_id?.trim()
                setActivePersonaId(sel && sel.length > 0 ? sel : 'ban_than')
            })
            .catch(() => {
                if (!cancelled) setError('Không tải được danh sách nhân vật.')
            })
            .finally(() => {
                if (!cancelled) setLoading(false)
            })
        return () => {
            cancelled = true
        }
    }, [])

    async function handleSelect(personaId: string) {
        if (personaId === activePersonaId) return
        setError(null)
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
                        {PERSONA_LABEL[p.persona_id] ?? p.persona_id}
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
