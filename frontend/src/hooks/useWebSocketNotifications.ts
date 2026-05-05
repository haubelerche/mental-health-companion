/**
 * WebSocket Notification Hook
 * Manages real-time WebSocket connection for receiving notifications
 * Uses HTTP-only cookie authentication (same as HTTP requests)
 */

import { useEffect, useRef, useCallback } from "react";
import { useNotification } from "../contexts/NotificationContext";

export interface WebSocketMessage {
  type: "notification" | "connected" | "ping" | "error";
  payload?: any;
  message?: string;
  user_id?: string;
  timestamp?: string;
}

interface UseWebSocketNotificationsOptions {
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

/**
 * Hook to manage WebSocket connection for notifications
 * Automatically connects when component mounts, handles reconnection logic
 * Uses HTTP-only cookie for authentication (secure, no token in JS)
 */
export const useWebSocketNotifications = (
  options: UseWebSocketNotificationsOptions = {}
) => {
  const { autoConnect = true, reconnectAttempts = 5, reconnectInterval = 3000 } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const { addNotification } = useNotification();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.debug("[WS] Already connected");
      return;
    }

    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      // Cookies are automatically sent with WebSocket connections
      const wsUrl = `${protocol}//${host}/v1/ws/notifications`;

      console.log("[WS] Connecting to:", wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("[WS] Connected successfully");
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.debug("[WS] Message:", message);

          switch (message.type) {
            case "connected":
              console.log(`[WS] ${message.message} - User: ${message.user_id}`);
              break;

            case "notification":
              if (message.payload) {
                console.log("[WS] New notification:", message.payload.notification_type);
                addNotification(message.payload);
              }
              break;

            case "error":
              console.error("[WS] Server error:", message.message);
              break;

            default:
              console.debug("[WS] Unknown message type:", message.type);
          }
        } catch (error) {
          console.error("[WS] Failed to parse message:", error);
        }
      };

      ws.onerror = (event) => {
        console.error("[WS] Connection error:", event);
      };

      ws.onclose = (event) => {
        console.log(`[WS] Disconnected (code: ${event.code}, reason: ${event.reason})`);
        wsRef.current = null;

        // Attempt reconnection (but not for auth errors)
        if (event.code !== 4001 && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          const delay = reconnectInterval * Math.pow(2, reconnectCountRef.current - 1);
          console.log(
            `[WS] Reconnecting in ${delay}ms (attempt ${reconnectCountRef.current}/${reconnectAttempts})`
          );
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else if (event.code === 4001) {
          console.warn("[WS] Authentication failed - not reconnecting");
        } else {
          console.warn("[WS] Max reconnection attempts reached");
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("[WS] Connection error:", error);
    }
  }, [addNotification, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    reconnectCountRef.current = 0;
  }, []);

  // Auto-connect when component mounts and when user is authenticated
  useEffect(() => {
    if (autoConnect) {
      // Add a small delay to ensure DOM is ready and cookies are available
      const timer = setTimeout(() => {
        connect();
      }, 100);
      
      return () => {
        clearTimeout(timer);
        disconnect();
      };
    }
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    connect,
    disconnect,
  };
};
