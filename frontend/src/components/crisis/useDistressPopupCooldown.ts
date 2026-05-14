import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'serene_distress_popup_dismissed_ids'

function readDismissedIds(): Set<string> {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        const parsed = raw ? JSON.parse(raw) : []
        return new Set(Array.isArray(parsed) ? parsed.map(String) : [])
    } catch {
        return new Set()
    }
}

function writeDismissedIds(ids: Set<string>) {
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(ids).slice(-40)))
    } catch {
        // Storage is a UX guard only; backend remains source of truth.
    }
}

export function useDistressPopupCooldown() {
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => readDismissedIds())

    useEffect(() => {
        writeDismissedIds(dismissedIds)
    }, [dismissedIds])

    const isDismissed = useCallback((popupId?: string | null) => {
        return Boolean(popupId && dismissedIds.has(popupId))
    }, [dismissedIds])

    const dismiss = useCallback((popupId?: string | null) => {
        if (!popupId) return
        setDismissedIds((prev) => {
            const next = new Set(prev)
            next.add(popupId)
            return next
        })
    }, [])

    return { isDismissed, dismiss }
}
