/**
 * Notification Toast Component
 * Displays real-time notifications as toasts
 */

import React, { useEffect, useState } from "react";
import { useNotification } from "../../contexts/NotificationContext";
import type { Notification } from "../../contexts/NotificationTypes";
import { X, AlertCircle, CheckCircle, Info, MessageSquare } from "lucide-react";

const NotificationToast: React.FC<{ notification: Notification; onClose: () => void }> = ({
  notification,
  onClose,
}) => {
  const [isExiting, setIsExiting] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // Small delay to trigger entrance animation
    const mountTimer = setTimeout(() => setIsMounted(true), 10);
    
    const exitTimer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(onClose, 500);
    }, 7000);

    return () => {
      clearTimeout(mountTimer);
      clearTimeout(exitTimer);
    };
  }, [onClose]);

  const getIcon = () => {
    switch (notification.notification_type) {
      case "letter.replied":
      case "letter.received":
        return <MessageSquare size={18} className="text-purple-500" />;
      case "letter.reported":
      case "crisis.detected":
        return <AlertCircle size={18} className="text-red-500" />;
      case "reward.earned":
        return <CheckCircle size={18} className="text-green-500" />;
      case "persona.unlocked":
      case "memory.completed":
        return <CheckCircle size={18} className="text-blue-500" />;
      default:
        return <Info size={18} className="text-gray-500" />;
    }
  };

  const getTypeClass = () => {
    if (notification.notification_type.startsWith("letter")) return "letter";
    if (notification.notification_type === "reward.earned") return "reward";
    if (notification.notification_type.includes("crisis") || notification.notification_type.includes("reported")) return "safety";
    return "system";
  };

  return (
    <div
      className={`notification-toast ${getTypeClass()} ${isMounted ? "show" : ""} ${isExiting ? "exit" : ""}`}
    >
      <div className="notification-icon">{getIcon()}</div>
      <div className="notification-content">
        <div className="notification-title">{notification.title}</div>
        <div className="notification-body">{notification.body}</div>
      </div>
      <button
        onClick={() => {
          setIsExiting(true);
          setTimeout(onClose, 500);
        }}
        className="notification-close"
      >
        <X size={16} />
      </button>
    </div>
  );
};

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="notification-container">
      {notifications.slice(0, 5).map((notification) => (
        <NotificationToast
          key={notification.notification_id}
          notification={notification}
          onClose={() => removeNotification(notification.notification_id)}
        />
      ))}
    </div>
  );
};

export default NotificationContainer;
