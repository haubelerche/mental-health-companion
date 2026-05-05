import { useEffect, useState } from 'react'
import { notificationService } from '../../services/notificationService'
import type { UserNotification } from '../../services/notificationService'
import Loading from '../ui/Loading'

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

export default function NotificationsPage({ dark = false }: { dark?: boolean }) {
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
    bg: dark ? 'bg-theme-surface' : 'bg-white',
    text: dark ? 'text-white' : 'text-slate-900',
    subtext: dark ? 'text-slate-400' : 'text-slate-500',
    card: dark ? 'bg-slate-800/40 border-slate-700/50' : 'bg-white border-slate-100',
    unread: dark ? 'bg-indigo-500/10 border-l-4 border-l-indigo-500' : 'bg-indigo-50 border-l-4 border-l-indigo-500',
  }

  if (loading) return <div className="h-screen flex items-center justify-center bg-slate-50"><Loading /></div>

  return (
    <div className={`min-h-screen pb-20 ${ui.bg} ${ui.text} font-sans`}>
      <div className="sticky top-0 z-20 backdrop-blur-md bg-opacity-80 border-b border-slate-200/20 px-6 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold font-display">Thông báo</h1>
        {unreadCount > 0 && (
          <button 
            onClick={handleMarkAllAsRead}
            className="text-sm font-medium text-indigo-500 hover:text-indigo-600 transition-colors"
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
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
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
                      <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                      <span className="text-[10px] font-medium text-indigo-500">Mới</span>
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
