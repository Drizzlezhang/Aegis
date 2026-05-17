import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearToken, getToken, isAuthenticated } from '@/lib/auth';

describe('auth token utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  it('returns null and clears token when expired', () => {
    vi.setSystemTime(new Date('2026-05-17T04:00:00Z'));
    localStorage.setItem('aegis_token', 'expired-token');
    localStorage.setItem('aegis_token_expires', String(Date.now() - 1000));

    expect(getToken()).toBeNull();
    expect(localStorage.getItem('aegis_token')).toBeNull();
    expect(localStorage.getItem('aegis_token_expires')).toBeNull();
  });

  it('clearToken removes storage entries', () => {
    localStorage.setItem('aegis_token', 'token');
    localStorage.setItem('aegis_token_expires', String(Date.now() + 1000));
    clearToken();
    expect(localStorage.getItem('aegis_token')).toBeNull();
    expect(localStorage.getItem('aegis_token_expires')).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });
});
