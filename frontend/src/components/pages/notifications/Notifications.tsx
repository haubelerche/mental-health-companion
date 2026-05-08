import { useEffect, useState } from 'react'
import { notificationService } from '../../../services/notificationService'
import type { UserNotification } from '../../../services/notificationService'
import Loading from '../../ui/Loading'

function timeAgo(dateParam: any) {
  if (!dateParam) return '---'
  try {
    const date = typeof dateParam === 'string' ? new Date(dateParam) : dateParam
    if (isNaN(date.getTime())) return '---'
    const now = new Date()
    const seconds = Math.round((now.getTime() - date.getTime()) / 1000)
    const minutes = Math.round(seconds / 60)
    const hours = Math.round(minutes / 60)
    const days = Math.round(hours / 24)
    if (seconds < 60) return 'vừa xong'
    if (minutes < 60) return `${minutes} phút trước`
    if (hours < 24) return `${hours} giờ trước`
    if (days < 7) return `${days} ngày trước`
    return date.toLocaleDateString('vi-VN')
  } catch (e) {
    return '---'
  }
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<UserNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)

  const fetchNotifications = async () => {
    try {
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
    fetchNotifications()
  }, [])

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
    bg: 'bg-theme-surface/60',
    text: 'text-theme-primary',
    subtext: 'text-theme-secondary',
    card: 'bg-theme-surface border-theme-primary/50',
    unread: 'bg-theme-surface/50 border-l-5 border-l-theme-accent',
  }

  if (loading) return <Loading />

  return (
    <div className={`min-h-screen  pb-20 ${ui.bg} ${ui.text} font-sans backdrop-blur-2xl rounded-4xl`}>
      <div className="w-full h-screen overflow-hidden rounded-4xl shadow-2xl border border-theme-primary/5">
        <img src={"./src/assets/background_image.png"} alt="" className="w-full h-full object-cover" />
      </div>
      <div className="sticky top-0 z-20  border-b border-theme-primary/70 bg-theme-surface rounded-t-2xl px-6 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold font-display">Thông báo</h1>
        {unreadCount > 0 && (
          <button 
            onClick={handleMarkAllAsRead}
            className="text-sm font-medium text-theme-accent hover:text-serene-secondary transition-colors"
          >
            Đánh dấu đã đọc tất cả
          </button>
        )}
      </div>

      <div className="max-w-2xl mx-auto mt-6 px-4">
        {(!notifications || notifications.length === 0) ? (
          <div className="text-center py-20">
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
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${n.is_read ? ui.card : ui.unread} hover:shadow-lg`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-shadow-theme-surface">
                      {n.notification_type?.replace('.', ' • ') || 'Thông báo'}
                    </span>
                    <span className={`text-[10px] ${ui.subtext}`}>
                      {timeAgo(n.created_at)}
                    </span>
                  </div>
                  <h3 className="font-semibold text-base mb-1">{n.title || 'Thông báo mới'}</h3>
                  <p className={`text-sm ${ui.subtext} leading-relaxed`}>{n.body || ''}</p>
                  
                  {!n.is_read && (
                    <div className="mt-3 flex items-center gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-theme-accent animate-pulse" />
                      <span className="text-sm font-medium text-theme-accent">Mới</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
