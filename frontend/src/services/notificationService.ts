import { httpClient } from '../api/httpClient'

export type UserNotification = {
  notification_id: string
  title: string
  body: string
  notification_type: string
  payload: Record<string, any> | null
  is_read: boolean
  created_at: string
}

export type NotificationsResponse = {
  notifications: UserNotification[]
  total: number
  unread_count: number
  has_more: boolean
}

export const notificationService = {
  async getNotifications(limit = 20, offset = 0): Promise<NotificationsResponse> {
    return httpClient.get<NotificationsResponse>(`/notifications?limit=${limit}&offset=${offset}`)
  },

  async markAsRead(notificationId: string): Promise<void> {
    await httpClient.postWithCsrf(`/notifications/${notificationId}/read`)
  },

  async markAllAsRead(): Promise<void> {
    await httpClient.postWithCsrf('/notifications/read-all')
  }
}
