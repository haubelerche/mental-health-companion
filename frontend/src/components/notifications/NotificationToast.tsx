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

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(onClose, 300);
    }, 7000);

    return () => clearTimeout(timer);
  }, [onClose]);

  const getIcon = () => {
    switch (notification.notification_type) {
      case "letter.replied":
        return <MessageSquare className="w-5 h-5 text-blue-500" />;
      case "letter.reported":
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case "letter.received":
        return <MessageSquare className="w-5 h-5 text-purple-500" />;
      case "reward.earned":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "persona.unlocked":
        return <CheckCircle className="w-5 h-5 text-yellow-500" />;
      case "memory.completed":
        return <CheckCircle className="w-5 h-5 text-indigo-500" />;
      default:
        return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getBgColor = () => {
    switch (notification.notification_type) {
      case "letter.replied":
        return "bg-blue-50 border-blue-200";
      case "letter.reported":
        return "bg-red-50 border-red-200";
      case "letter.received":
        return "bg-purple-50 border-purple-200";
      case "reward.earned":
        return "bg-green-50 border-green-200";
      case "persona.unlocked":
        return "bg-yellow-50 border-yellow-200";
      case "memory.completed":
        return "bg-indigo-50 border-indigo-200";
      default:
        return "bg-gray-50 border-gray-200";
    }
  };

  return (
    <div
      className={`
        transform transition-all duration-300
        ${isExiting ? "translate-x-96 opacity-0" : "translate-x-0 opacity-100"}
      `}
    >
      <div
        className={`
          ${getBgColor()}
          border rounded-lg shadow-lg p-4 mb-3 flex items-start gap-3
          max-w-md
        `}
      >
        <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-gray-900">{notification.title}</p>
          <p className="text-sm text-gray-600 mt-1">{notification.body}</p>
        </div>
        <button
          onClick={() => {
            setIsExiting(true);
            setTimeout(onClose, 300);
          }}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="fixed bottom-0 right-0 p-4 pointer-events-none z-50">
      <div className="flex flex-col gap-2 pointer-events-auto">
        {notifications.slice(0, 5).map((notification) => (
          <NotificationToast
            key={notification.notification_id}
            notification={notification}
            onClose={() => removeNotification(notification.notification_id)}
          />
        ))}
      </div>
    </div>
  );
};

export default NotificationContainer;
