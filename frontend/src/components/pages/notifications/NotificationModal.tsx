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
        bg: 'bg-[#f8e7b8]',
        text: 'text-[#3d2b1b]',
        subtext: 'text-[#5f5140]',
        card: 'bg-[#fff6d5] border-2 border-[#6b4b2a]',
        unread: 'bg-[#fff6d5] border-2 border-[#5c3b24] shadow-[2px_2px_0_rgba(55,38,20,0.25)]',
    }

    return (
        <Modal
            isOpen={open}
            onRequestClose={onClose}
            shouldCloseOnEsc
            shouldCloseOnOverlayClick
            contentLabel="Thông báo"
            className="relative z-[81] mb-5 flex max-h-[80dvh] w-full max-w-2xl flex-col overflow-hidden border-4 border-[#6b4b2a] bg-[#f8e7b8] shadow-[0_7px_0_rgba(55,38,20,0.35)] outline-none"
            overlayClassName="fixed inset-0 z-[80] flex items-end justify-center sm:items-center bg-black/50 backdrop-blur-xs"
        >
            <div className={`flex items-center justify-between border-b-4 border-[#5c3b24] bg-[#8a6040] px-5 py-4 text-[#fff6d5]`}>
                <div>
                    <p className={`text-sm font-black uppercase tracking-[0.22em] text-[#fff6d5]`}>
                        Thông báo
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    {unreadCount > 0 && (
                        <button
                            onClick={handleMarkAllAsRead}
                            className="border-2 border-[#7c5936] bg-[#fff6d5] px-3 py-1 text-xs font-black text-[#6b4b2a] hover:bg-[#f2d89e] transition-colors cursor-pointer"
                        >
                            Đọc tất cả
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={onClose}
                        className="border-2 border-[#6b4b2a] bg-[#fff6d5] text-[#5c3b24] p-1.5 hover:bg-[#f2d89e] transition-colors cursor-pointer"
                    >
                        <X className="h-4 w-4" />
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
                                    className={`p-4 border transition-all cursor-pointer ${n.is_read ? ui.card : ui.unread} hover:bg-[#f2d89e]`}
                                >
                                    <div className="flex justify-between items-start mb-1">
                                        <span className={`text-xs font-black uppercase tracking-wider ${ui.text}`}>
                                            {n.notification_type?.replace('.', ' • ') || 'Thông báo'}
                                        </span>
                                        <span className={`text-[10px] font-bold ${ui.subtext}`}>
                                            {parseTime(n.created_at)}
                                        </span>
                                    </div>
                                    <h3 className={`font-black text-sm mb-1 ${ui.text}`}>{n.title || 'Thông báo mới'}</h3>
                                    <p className={`text-xs font-bold ${ui.subtext} leading-relaxed`}>{n.body || ''}</p>

                                    {!n.is_read && (
                                        <div className="mt-3 flex items-center gap-1.5">
                                            <div className="w-3 h-3 bg-[#8a6040] border border-[#5c3b24]" />
                                            <span className="text-xs font-black text-[#8a6040]">Mới</span>
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
