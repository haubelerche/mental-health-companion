/* eslint-disable react-refresh/only-export-components */
/**
 * Notification Context
 * Global state management for real-time notifications
 */

import React, { createContext, useContext, useCallback, useState } from "react";
import type { Notification } from "./NotificationTypes";

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Notification) => void;
  removeNotification: (notificationId: string) => void;
  markAsRead: (notificationId: string) => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((notification: Notification) => {
    console.log("[Notification] Added:", notification);
    setNotifications((prev) => [
      { ...notification, is_read: false },
      ...prev.slice(0, 99), // Keep last 100 notifications
    ]);

    // Auto-remove after 30 seconds if not read
    window.setTimeout(() => {
      setNotifications((prev) =>
        prev.filter((n) => n.notification_id !== notification.notification_id)
      );
    }, 30000);
  }, []);

  const removeNotification = useCallback((notificationId: string) => {
    setNotifications((prev) => prev.filter((n) => n.notification_id !== notificationId));
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.notification_id === notificationId ? { ...n, is_read: true } : n))
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        addNotification,
        removeNotification,
        markAsRead,
        clearAll,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotification must be used within NotificationProvider");
  }
  return context;
};
