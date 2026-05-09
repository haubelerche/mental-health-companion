import { useEffect, useState } from 'react'
import { notificationService } from '../../../services/notificationService'
import type { UserNotification } from '../../../services/notificationService'
import Loading from '../../ui/Loading'
import { parseTime } from '@/utils/parseTime'
import { X } from 'lucide-react'
import Modal from 'react-modal'

type Props = {
    open: boolean
    onClose: () => void
}

export default function NotificationModal({ open, onClose }: Props) {
    const [notifications, setNotifications] = useState<UserNotification[]>([])
    const [loading, setLoading] = useState(true)
    const [unreadCount, setUnreadCount] = useState(0)

    useEffect(() => {
        if (typeof document !== 'undefined') {
            Modal.setAppElement('#root')
        }
    }, [])

    const fetchNotifications = async () => {
        try {
            setLoading(true)
            const data = await notificationService.getNotifications()
            if (data && Array.isArray(data.notifications)) {
                setNotifications(data.notifications)
                setUnreadCount(data.unread_count || 0)
            }
        } catch (err) {
            console.error('Failed to fetch notifications:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (open) {
            fetchNotifications()
        }
    }, [open])

    const handleMarkAsRead = async (id: string) => {
        try {
            await notificationService.markAsRead(id)
            setNotifications(prev =>
                (prev || []).map(n => n.notification_id === id ? { ...n, is_read: true } : n)
            )
            setUnreadCount(prev => Math.max(0, prev - 1))
        } catch (err) {
            console.error('Failed to mark as read:', err)
        }
    }

    const handleMarkAllAsRead = async () => {
        try {
            await notificationService.markAllAsRead()
            setNotifications(prev => (prev || []).map(n => ({ ...n, is_read: true })))
            setUnreadCount(0)
        } catch (err) {
            console.error('Failed to mark all as read:', err)
        }
    }

    const ui = {
        bg: 'bg-theme-surface',
        text: 'text-theme-primary',
        subtext: 'text-theme-secondary',
        card: 'bg-theme-surface border-theme-primary/50',
        unread: 'bg-theme-surface/50 border-l-4 border-l-theme-accent',
    }

    return (
        <Modal
            isOpen={open}
            onRequestClose={onClose}
            shouldCloseOnEsc
            shouldCloseOnOverlayClick
            contentLabel="Thông báo"
            className="relative z-[81] mb-5 flex max-h-[80dvh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border shadow-2xl border-theme-border bg-theme-surface outline-none"
            overlayClassName="fixed inset-0 z-[80] flex items-end justify-center sm:items-center bg-black/50 backdrop-blur-xs"
        >
            <div className={`flex items-center justify-between border-b px-5 py-4 border-theme-secondary/40`}>
                <div>
                    <p className={`text-sm font-semibold mb-1 uppercase tracking-[0.22em] text-theme-text-secondary`}>
                        Thông báo
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    {unreadCount > 0 && (
                        <button
                            onClick={handleMarkAllAsRead}
                            className="text-sm cursor-pointer font-medium text-theme-accent hover:text-theme-primary transition-colors"
                        >
                            Đọc tất cả
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={onClose}
                        className={`rounded-full cursor-pointer p-2 hover:text-red-400`}
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
            </div>

            <div className="overflow-y-auto px-5 pb-8 pt-4">
                {loading ? (
                    <Loading />
                ) : (!notifications || notifications.length === 0) ? (
                    <div className="text-center py-10">
                        <div className="text-6xl mb-4">🔔</div>
                        <p className={ui.subtext}>Bạn chưa có thông báo nào.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {notifications.map((n) => {
                            if (!n) return null
                            return (
                                <div
                                    key={n.notification_id || Math.random()}
                                    onClick={() => !n.is_read && handleMarkAsRead(n.notification_id)}
                                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${n.is_read ? ui.card : ui.unread} hover:bg-theme-accent/10`}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="text-xs font-bold uppercase tracking-wider">
                                            {n.notification_type?.replace('.', ' • ') || 'Thông báo'}
                                        </span>
                                        <span className={`text-[10px] ${ui.subtext}`}>
                                            {parseTime(n.created_at)}
                                        </span>
                                    </div>
                                    <h3 className="font-semibold text-base mb-1">{n.title || 'Thông báo mới'}</h3>
                                    <p className={`text-sm ${ui.subtext} leading-relaxed`}>{n.body || ''}</p>

                                    {!n.is_read && (
                                        <div className="mt-3 flex items-center gap-1.5">
                                            <div className="w-3 h-3 rounded-full bg-theme-accent" />
                                            <span className="text-sm font-medium text-theme-accent">Mới</span>
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </Modal>
    )
}
