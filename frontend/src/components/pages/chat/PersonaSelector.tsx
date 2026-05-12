import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'react-toastify'

import { ApiRequestError } from '../../../api/types'
import {
    DEFAULT_PERSONA_ID,
    PERSONA_DISPLAY_NAME,
    PERSONA_IDS,
    PERSONA_SHORT_DESCRIPTION,
    isPersonaId,
} from '../../../constants/personas'
import { ROUTE_PATHS } from '../../../routes/paths'
import type { PersonaProgress } from '../../../services/rewardsService'
import { chatService } from '../../../services/chatService'
import { personasService } from '../../../services/personasService'

const FETCH_TIMEOUT_MS = 20_000
const PERSONA_ORDER = PERSONA_IDS

function buildFallbackPersonasProgress(): PersonaProgress[] {
    return [
        { persona_id: 'dung_luong', unlocked: true, is_core: true, price_hearts: null },
        { persona_id: 'dat_le', unlocked: true, is_core: true, price_hearts: null },
        { persona_id: 'hau_luong', unlocked: false, is_core: false, price_hearts: 500 },
    ]
}

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
    let timeoutId: ReturnType<typeof setTimeout> | undefined
    const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = window.setTimeout(() => reject(new Error(`timeout:${label}`)), ms)
    })
    return Promise.race([promise, timeoutPromise]).finally(() => {
        if (timeoutId !== undefined) window.clearTimeout(timeoutId)
    }) as Promise<T>
}

type Props = {
    onSelect?: (personaId: string) => void
}

export default function PersonaSelector({ onSelect }: Props) {
    const [progress, setProgress] = useState<PersonaProgress[]>(buildFallbackPersonasProgress)
    const [activePersonaId, setActivePersonaId] = useState<string>(DEFAULT_PERSONA_ID)
    const [profileSyncError, setProfileSyncError] = useState<string | null>(null)

    const selectablePersonas = useMemo(() => {
        const byId = new Map(progress.filter((p) => isPersonaId(p.persona_id)).map((p) => [p.persona_id, p]))
        return PERSONA_ORDER.map((id) => byId.get(id)).filter((p): p is PersonaProgress => Boolean(p))
    }, [progress])

    useEffect(() => {
        let cancelled = false
        void (async () => {
            const [meRes, progRes] = await Promise.allSettled([
                withTimeout(personasService.getMe(), FETCH_TIMEOUT_MS, 'profile'),
                withTimeout(chatService.getPersonasProgress(), FETCH_TIMEOUT_MS, 'personas_progress'),
            ])
            if (cancelled) return
            if (meRes.status === 'fulfilled') {
                setProfileSyncError(null)
                setActivePersonaId(isPersonaId(meRes.value.persona_id) ? meRes.value.persona_id : DEFAULT_PERSONA_ID)
            } else {
                const reason = meRes.reason
                const isTimeout = reason instanceof Error && reason.message.startsWith('timeout:')
                setProfileSyncError(
                    isTimeout
                        ? 'Chưa đồng bộ được nhân vật đang chọn (mạng chậm). F5 nếu vẫn sai.'
                        : 'Chưa tải được hồ sơ; đang dùng mặc định. Kiểm tra đăng nhập và thử lại.',
                )
            }
            if (progRes.status === 'fulfilled') {
                setProgress(progRes.value.personas)
            }
        })()
        return () => {
            cancelled = true
        }
    }, [])

    async function handleSelect(personaId: string) {
        if (personaId === activePersonaId) return
        setProfileSyncError(null)

        const persona = selectablePersonas.find((item) => item.persona_id === personaId)
        if (persona && !persona.is_core && !persona.unlocked) {
            toast.info('Hậu đang bị khóa. Hãy tích đủ 500 tim rồi vào Cửa hàng Thưởng để giải cứu nhé!')
            return
        }

        try {
            const res = await personasService.select(personaId)
            const resolvedPersonaId = isPersonaId(res.persona_id) ? res.persona_id : personaId
            setActivePersonaId(resolvedPersonaId)
            onSelect?.(resolvedPersonaId)
        } catch (err) {
            if (err instanceof ApiRequestError) setProfileSyncError(err.message)
            else setProfileSyncError('Không đổi được nhân vật lúc này.')
        }
    }

    const value =
        selectablePersonas.some((p) => p.persona_id === activePersonaId) ? activePersonaId : selectablePersonas[0]?.persona_id
    const selectedDescription = PERSONA_SHORT_DESCRIPTION[value || DEFAULT_PERSONA_ID]
    const selectedIsLocked = value === 'hau_luong' && selectablePersonas.some((p) => p.persona_id === 'hau_luong' && !p.unlocked)

    return (
        <div className="space-y-2">
            {profileSyncError ? (
                <p className="text-[11px] leading-snug text-amber-200/90" role="status">
                    {profileSyncError}
                </p>
            ) : null}
            <label className="sr-only" htmlFor="persona-select">
                Chọn nhân vật
            </label>
            <select
                id="persona-select"
                value={value || DEFAULT_PERSONA_ID}
                onChange={(e) => void handleSelect(e.target.value)}
                className="w-full rounded-lg border border-theme-border/40 bg-theme-surface/60 px-3 py-2 text-sm text-theme-text-primary"
            >
                {selectablePersonas.map((p) => (
                    <option key={p.persona_id} value={p.persona_id}>
                        {PERSONA_DISPLAY_NAME[p.persona_id] ?? p.persona_id} {!p.is_core && !p.unlocked ? ' (bị khóa)' : ''}
                    </option>
                ))}
            </select>
            <p className="text-[11px] leading-snug text-theme-text-secondary">{selectedDescription}</p>
            {selectedIsLocked ? (
                <p className="text-[11px] leading-snug text-theme-text-secondary">
                    Hậu đang bị khóa, cần 500 tim trong{' '}
                    <Link to={ROUTE_PATHS.rewards} className="font-medium text-theme-accent underline underline-offset-2">
                        Cửa hàng Thưởng
                    </Link>
                    .
                </p>
            ) : null}
        </div>
    )
}
