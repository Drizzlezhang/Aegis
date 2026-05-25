'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

interface PipelineStep {
  index: number;
  total: number;
  agent: string;
  status: 'started' | 'completed' | 'failed';
  elapsedMs?: number;
}

interface PipelineProgressEvent {
  type: 'pipeline_progress';
  request_id: string;
  step: PipelineStep;
}

interface UseAnalysisSocketReturn {
  steps: PipelineStep[];
  isConnected: boolean;
  currentStep: number;
  totalSteps: number;
  isComplete: boolean;
  error: string | null;
}

const MAX_RECONNECT = 3;
const RECONNECT_INTERVAL_MS = 2000;

export function useAnalysisSocket(requestId: string | null): UseAnalysisSocketReturn {
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.onopen = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!requestId) return;
    cleanup();

    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
    const url = `${protocol}//${host}/ws/analysis/${requestId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setIsConnected(true);
      reconnectCountRef.current = 0;
      setError(null);
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data: PipelineProgressEvent = JSON.parse(event.data);
        if (data.type === 'pipeline_progress' && data.step) {
          setSteps((prev) => {
            const existing = prev.findIndex((s) => s.index === data.step.index);
            if (existing >= 0) {
              const updated = [...prev];
              updated[existing] = data.step;
              return updated;
            }
            return [...prev, data.step];
          });
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (reconnectCountRef.current < MAX_RECONNECT) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectCountRef.current += 1;
          connect();
        }, RECONNECT_INTERVAL_MS);
      } else {
        setError('Connection lost after max retries');
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      ws.close();
    };
  }, [requestId, cleanup]);

  useEffect(() => {
    mountedRef.current = true;
    if (requestId) {
      connect();
    } else {
      setSteps([]);
      setIsConnected(false);
      setError(null);
    }
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [requestId, connect, cleanup]);

  const currentStep = steps.length > 0 ? steps[steps.length - 1].index : -1;
  const totalSteps = steps.length > 0 ? steps[0].total : 0;
  const isComplete =
    steps.length > 0 &&
    steps[steps.length - 1].index === steps[0].total - 1 &&
    steps[steps.length - 1].status === 'completed';

  return { steps, isConnected, currentStep, totalSteps, isComplete, error };
}
