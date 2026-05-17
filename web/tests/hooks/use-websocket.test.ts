import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocket';

let server: any;
let sendSpy: ((data: string) => void) | null = null;

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    server.clients.add(this);
    setTimeout(() => {
      this.readyState = 1;
      this.onopen?.();
    }, 0);
  }
  send(data: string) {
    sendSpy?.(data);
  }
  close() {
    this.readyState = 3;
    server.clients.delete(this);
    this.onclose?.();
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    sendSpy = null;
    server = {
      clients: new Set<any>(),
      send(msg: string) {
        this.clients.forEach((client: any) => client.onmessage?.({ data: msg }));
      },
      close() {
        this.clients.forEach((client: any) => client.onclose?.());
      },
    };
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('initial status is disconnected when no url', () => {
    const { result } = renderHook(() => useWebSocket(null));
    expect(result.current.status).toBe('disconnected');
  });

  it('connects on mount', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:1234'));
    await waitFor(() => expect(result.current.status).toBe('connected'));
  });

  it('reconnects on close with backoff', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { result } = renderHook(() => useWebSocket('ws://localhost:1234'));
    await waitFor(() => expect(result.current.status).toBe('connected'));

    act(() => {
      server.close();
    });

    await waitFor(() => expect(result.current.status).toBe('reconnecting'));

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => expect(result.current.status).toBe('connected'));
    vi.useRealTimers();
  });

  it('cleanup on unmount', async () => {
    const { result, unmount } = renderHook(() => useWebSocket('ws://localhost:1234'));
    await waitFor(() => expect(result.current.status).toBe('connected'));

    unmount();
    // Should not throw and ws should be closed
    expect(server.clients.size).toBe(0);
  });

  it('heartbeat ping sent', async () => {
    vi.useRealTimers();
    sendSpy = vi.fn<(data: string) => void>();

    const { result } = renderHook(() => useWebSocket('ws://localhost:1234', { heartbeatInterval: 50 }));
    await waitFor(() => expect(result.current.status).toBe('connected'));

    await waitFor(() => expect(sendSpy).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' })), { timeout: 2000 });
  });

  it('message parsing', async () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket('ws://localhost:1234', { onMessage }));
    await waitFor(() => expect(result.current.status).toBe('connected'));

    act(() => {
      server.send(JSON.stringify({ type: 'update', symbol: 'AAPL', price: 150 }));
    });

    await waitFor(() => expect(result.current.lastMessage).toEqual({ type: 'update', symbol: 'AAPL', price: 150 }));
    expect(onMessage).toHaveBeenCalledWith({ type: 'update', symbol: 'AAPL', price: 150 });
  });
});
