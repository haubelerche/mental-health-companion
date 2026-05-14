import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNotification } from '../../contexts/NotificationContext'
import { useAuth } from '../../hooks/useAuth'
import { notificationService, type UserNotification } from '../../services/notificationService'
import RealtimeNotificationAssistant, { type AppNotification } from './RealtimeNotificationAssistant'
import { OPEN_NOTIFICATION_MODAL_EVENT } from '../pages/notifications/events'

function routeFromPayload(payload: Record<string, unknown> | null | undefined): string | undefined {
    return typeof payload?.route === 'string' ? payload.route : undefined
}

function toAppNotification(item: UserNotification): AppNotification {
    return {
        id: item.notification_id,
        title: item.title,
        body: item.body,
        created_at: item.created_at,
        route: routeFromPayload(item.payload),
    }
}

export default function RealtimeNotificationAssistantBridge() {
    const navigate = useNavigate()
    const { user } = useAuth()
    const { notifications, removeNotification, markAsRead } = useNotification()
    const [apiNotifications, setApiNotifications] = useState<UserNotification[]>([])
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => new Set())

    const refreshUnreadNotifications = useCallback(async () => {
        try {
            const data = await notificationService.getNotifications(10, 0)
            setApiNotifications((data.notifications || []).filter((item) => !item.is_read))
        } catch {
            // Notification assistant is non-critical UI. The notification center remains source of truth.
        }
    }, [])

    useEffect(() => {
        if (user) {
            void refreshUnreadNotifications()
        }
    }, [refreshUnreadNotifications, user])

    const safeNotifications = useMemo<AppNotification[]>(() => {
        const fromRealtime: AppNotification[] = notifications
            .filter((item) => !item.is_read)
            .map((item) => {
                const route = typeof item.data?.route === 'string' ? item.data.route : undefined
                return {
                    id: item.notification_id,
                    title: item.title,
                    body: item.body,
                    created_at: item.created_at ?? new Date().toISOString(),
                    route,
                }
            })

        const merged = new Map<string, AppNotification>()
        for (const item of [...apiNotifications.map(toAppNotification), ...fromRealtime]) {
            if (!dismissedIds.has(item.id)) merged.set(item.id, item)
        }

        return [...merged.values()]
            .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
            .slice(0, 1)
    }, [apiNotifications, dismissedIds, notifications])

    const latest = safeNotifications[0]

    const dismiss = (id: string) => {
        setDismissedIds((prev) => new Set(prev).add(id))
        markAsRead(id)
        removeNotification(id)
        void notificationService.markAsRead(id).then(refreshUnreadNotifications).catch(() => undefined)
    }

    return (
        <RealtimeNotificationAssistant
            notifications={safeNotifications}
            onDismiss={dismiss}
            onOpenNotificationCenter={() => {
                if (!latest) return
                dismiss(latest.id)
                if (latest.route) {
                    navigate(latest.route)
                    return
                }
                window.dispatchEvent(new Event(OPEN_NOTIFICATION_MODAL_EVENT))
            }}
        />
    )
}
