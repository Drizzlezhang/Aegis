import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('useWebSocket reconnect source checks', () => {
  const filePath = path.resolve(process.cwd(), 'hooks/useWebSocket.ts');
  const source = readFileSync(filePath, 'utf8');

  it('supports max reconnect attempts', () => {
    expect(source).toContain('maxReconnectAttempts');
    expect(source).toContain('reconnectCountRef.current < maxReconnectAttempts');
  });

  it('sets disconnected status when retry limit is reached', () => {
    expect(source).toContain("setStatus('disconnected')");
    expect(source).toContain("setStatus('reconnecting')");
  });

  it('resets reconnect count on successful connection', () => {
    expect(source).toContain('reconnectCountRef.current = 0');
  });
});
