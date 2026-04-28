export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'aegis-theme-mode';

function isThemeMode(value: string | null): value is ThemeMode {
  return value === 'light' || value === 'dark';
}

export function readStoredThemeMode(initialMode: ThemeMode): ThemeMode {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isThemeMode(stored) ? stored : initialMode;
}

export function writeStoredThemeMode(mode: ThemeMode) {
  window.localStorage.setItem(STORAGE_KEY, mode);
}

export function resolveInitialThemeMode(): ThemeMode {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (isThemeMode(stored)) {
    return stored;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
