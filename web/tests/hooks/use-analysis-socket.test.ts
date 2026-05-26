import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAnalysisSocket } from '@/hooks/useAnalysisSocket';

// Mock WebSocket
class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState: number = WebSocket.CONNECTING;

  static instances: MockWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  send(_data: string) {}
}

// Replace global WebSocket
const originalWebSocket = globalThis.WebSocket;

beforeEach(() => {
  MockWebSocket.instances = [];
  (globalThis as any).WebSocket = MockWebSocket;
  vi.useFakeTimers();
});

afterEach(() => {
  (globalThis as any).WebSocket = originalWebSocket;
  vi.useRealTimers();
});

describe('useAnalysisSocket', () => {
  it('returns initial state when requestId is null', () => {
    const { result } = renderHook(() => useAnalysisSocket(null));

    expect(result.current.steps).toEqual([]);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.currentStep).toBe(-1);
    expect(result.current.totalSteps).toBe(0);
    expect(result.current.isComplete).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('connects when requestId is provided', () => {
    const { result } = renderHook(() => useAnalysisSocket('test-123'));

    // Simulate WebSocket open
    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();
    expect(ws.url).toContain('/ws/analysis/test-123');

    act(() => {
      ws.onopen?.();
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('updates steps on pipeline_progress message', () => {
    const { result } = renderHook(() => useAnalysisSocket('test-456'));

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onopen?.();
    });

    // Simulate receiving a progress event
    act(() => {
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'pipeline_progress',
          request_id: 'test-456',
          step: {
            index: 0,
            total: 6,
            agent: 'Data-Harvester',
            status: 'started',
          },
        }),
      }));
    });

    expect(result.current.steps.length).toBe(1);
    expect(result.current.steps[0].agent).toBe('Data-Harvester');
    expect(result.current.steps[0].status).toBe('started');
    expect(result.current.currentStep).toBe(0);
    expect(result.current.totalSteps).toBe(6);
  });

  it('handles reconnect on close', () => {
    const { result } = renderHook(() => useAnalysisSocket('test-789'));

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.onopen?.();
    });
    expect(result.current.isConnected).toBe(true);

    // Simulate close
    act(() => {
      ws.onclose?.(new CloseEvent('close'));
    });
    expect(result.current.isConnected).toBe(false);

    // Advance timer for reconnect
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // A new WebSocket should have been created
    expect(MockWebSocket.instances.length).toBe(2);
    const ws2 = MockWebSocket.instances[1];
    act(() => {
      ws2.onopen?.();
    });
    expect(result.current.isConnected).toBe(true);
  });

  it('sets error after max reconnect attempts', () => {
    const { result } = renderHook(() => useAnalysisSocket('test-max'));

    // Initial connection succeeds then fails
    const ws0 = MockWebSocket.instances[0];
    act(() => {
      ws0.onopen?.();
    });
    act(() => {
      ws0.onclose?.(new CloseEvent('close'));
    });

    // 3 reconnect attempts, all fail (no onopen, simulate via onerror → close → onclose)
    for (let i = 0; i < 3; i++) {
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      const ws = MockWebSocket.instances[i + 1];
      act(() => {
        ws.onerror?.();
      });
    }

    expect(result.current.error).toBe('Connection lost after max retries');
  });

  it('cleans up on unmount', () => {
    const { unmount } = renderHook(() => useAnalysisSocket('test-cleanup'));

    const ws = MockWebSocket.instances[0];
    const closeSpy = vi.spyOn(ws, 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });
});
