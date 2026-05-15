import { describe, expect, it, vi } from 'vitest';
import { readStoredThemeMode, resolveInitialThemeMode, writeStoredThemeMode } from '@/lib/theme/theme-storage';

describe('theme storage helpers', () => {
  it('reads a stored theme mode when it is supported', () => {
    window.localStorage.setItem('aegis-theme-mode', 'light');

    expect(readStoredThemeMode('dark')).toBe('light');
  });

  it('falls back to the initial mode when storage is empty or invalid', () => {
    window.localStorage.removeItem('aegis-theme-mode');
    expect(readStoredThemeMode('dark')).toBe('dark');

    window.localStorage.setItem('aegis-theme-mode', 'system');
    expect(readStoredThemeMode('light')).toBe('light');
  });

  it('writes theme mode to localStorage', () => {
    writeStoredThemeMode('dark');

    expect(window.localStorage.getItem('aegis-theme-mode')).toBe('dark');
  });

  it('resolves light mode when browser prefers light and no storage override exists', () => {
    window.localStorage.removeItem('aegis-theme-mode');
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-color-scheme: dark)' ? false : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    expect(resolveInitialThemeMode()).toBe('light');
  });

  it('prefers stored mode over browser preference', () => {
    window.localStorage.setItem('aegis-theme-mode', 'dark');
    window.matchMedia = vi.fn().mockImplementation(() => ({
      matches: false,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    expect(resolveInitialThemeMode()).toBe('dark');
  });
});
