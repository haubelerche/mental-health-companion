/**
 * WebSocket Notification Hook
 * Manages real-time WebSocket connection for receiving notifications
 * Uses HTTP-only cookie authentication (same as HTTP requests)
 */

import { useEffect, useRef, useCallback } from "react";
import { useState } from "react";
import { useNotification } from "../contexts/NotificationContext";
import { getWebSocketBaseUrl } from "../api/httpClient";
import type { Notification } from "../contexts/NotificationTypes";

export interface WebSocketMessage {
  type: "notification" | "connected" | "ping" | "error";
  payload?: Record<string, unknown>;
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
  const connectRef = useRef<() => void>(() => {});
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const manualCloseRef = useRef(false);
  const { addNotification } = useNotification();
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }
    try {
      manualCloseRef.current = false;
      const wsBaseUrl = getWebSocketBaseUrl();
      if (!wsBaseUrl) {
        console.warn("[WS] WebSocket base URL is not configured");
        return;
      }
      const wsUrl = `${wsBaseUrl}/v1/ws/notifications`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        reconnectCountRef.current = 0;
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case "connected":
              break;

            case "notification":
              if (message.payload) {
                const payload = message.payload as Partial<Notification>;
                if (payload.notification_id && payload.notification_type && payload.title && payload.body) {
                  addNotification(payload as Notification);
                }
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
        wsRef.current = null;
        setIsConnected(false);

        if (manualCloseRef.current) {
          manualCloseRef.current = false;
          reconnectCountRef.current = 0;
          return;
        }

        // Attempt reconnection (but not for auth errors)
        if (event.code !== 4001 && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          const delay = reconnectInterval * Math.pow(2, reconnectCountRef.current - 1);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connectRef.current();
          }, delay);
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

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    if (reconnectTimeoutRef.current !== undefined) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
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
    isConnected,
    connect,
    disconnect,
  };
};
