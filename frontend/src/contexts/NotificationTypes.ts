/**
 * Notification Type Definitions
 */

export interface Notification {
  notification_id: string;
  notification_type: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  created_at?: string;
  is_read?: boolean;
}
