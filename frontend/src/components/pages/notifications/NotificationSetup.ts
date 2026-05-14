/**
 * Notification Setup Component
 * Initializes WebSocket connection when app loads
 * This component ensures the WebSocket hook runs at the app level
 */

import { useWebSocketNotifications } from "../../../hooks/useWebSocketNotifications";
import { useAuth } from "../../../hooks/useAuth";

const NotificationSetup = () => {
  const { user } = useAuth();
  
  // Initialize WebSocket connection
  // The hook will auto-connect and handle reconnection logic
  const { isConnected } = useWebSocketNotifications({
    autoConnect: !!user,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
  });

  // Log connection status for debugging
  if (isConnected) {
    console.debug("[Notification] WebSocket is connected");
  }

  // This component only manages the WebSocket connection
  // It doesn't render anything
  return null;
};

export default NotificationSetup;
