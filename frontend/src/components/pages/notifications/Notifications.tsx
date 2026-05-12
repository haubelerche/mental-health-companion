import { useEffect, useState } from 'react'
import { notificationService } from '../../../services/notificationService'
import type { UserNotification } from '../../../services/notificationService'
import Loading from '../../ui/Loading'
import bg from '../../../assets/motion/cat-soul.gif'
import { parseTime } from '@/utils/parseTime'
import PixelEmptyState from '../../pixel/PixelEmptyState'


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
    unread: 'bg-theme-surface/50 border-l-4 border-l-theme-accent',
  }

  if (loading) return <Loading />

  return (
    <div className="relative min-h-screen overflow-hidden text-theme-text-primary pb-20 ">
      <div className="fixed inset-0 z-0">
        <img src={bg} alt="Background" className="h-full w-full object-cover" />
      </div>
      
      <div className="relative z-10 mx-auto max-w-2xl px-4 py-6 md:py-8">
        <div className="rounded-[2.5rem] bg-theme-surface/85 backdrop-blur-sm p-6 md:p-8">
          
          <div className="mb-10 flex items-center justify-between border-b border-theme-secondary/30 pb-4">
            <h1 className="text-2xl font-bold font-display">Thông báo</h1>
            {unreadCount > 0 && (
              <button 
                onClick={handleMarkAllAsRead}
                className="text-sm cursor-pointer font-medium text-theme-accent hover:text-theme-primary transition-colors"
              >
                Đánh dấu đã đọc tất cả
              </button>
            )}
          </div>

          <div>
            {(!notifications || notifications.length === 0) ? (
              <PixelEmptyState
                mascot="bucket"
                title="Chưa có thông báo nào"
                description="Khi có cập nhật thật từ hệ thống, thông báo sẽ xuất hiện tại đây."
              />
            ) : (
              <div className="space-y-3">
                {notifications.map((n) => {
                  if (!n) return null
                  return (
                    <div 
                      key={n.notification_id || Math.random()}
                      onClick={() => !n.is_read && handleMarkAsRead(n.notification_id)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer ${n.is_read ? ui.card : ui.unread} hover:shadow-lg transition-all duration-300`}
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
        </div>
      </div>
    </div>
  )
}
