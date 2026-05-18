import { useEffect, useRef, useState, useCallback } from 'react';

export type WebSocketStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

interface UseWebSocketOptions {
  reconnectAttempts?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onMessage?: (data: any) => void;
}

interface UseWebSocketReturn {
  status: WebSocketStatus;
  lastMessage: any | null;
  sendMessage: (data: string | object) => void;
  reconnect: () => void;
}

export function useWebSocket(
  url: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const {
    reconnectAttempts,
    maxReconnectAttempts = reconnectAttempts ?? 10,
    heartbeatInterval = 30000,
    onMessage,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!url) return;
    cleanup();
    setStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      reconnectCountRef.current = 0;
      heartbeatTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, heartbeatInterval);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;
        setLastMessage(data);
        onMessage?.(data);
      } catch {
        setLastMessage(event.data);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
      if (reconnectCountRef.current < maxReconnectAttempts) {
        setStatus('reconnecting');
        const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 30000);
        reconnectTimerRef.current = setTimeout(() => {
          reconnectCountRef.current += 1;
          connect();
        }, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, heartbeatInterval, maxReconnectAttempts, onMessage, cleanup]);

  const sendMessage = useCallback((data: string | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const msg = typeof data === 'string' ? data : JSON.stringify(data);
      wsRef.current.send(msg);
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectCountRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    return cleanup;
  }, [connect, cleanup]);

  return { status, lastMessage, sendMessage, reconnect };
}
