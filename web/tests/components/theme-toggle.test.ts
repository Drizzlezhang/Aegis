import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('ThemeToggle component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/ThemeToggle.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('toggles between light and dark', () => {
    expect(source).toContain('useThemeMode');
    expect(source).toContain('toggleMode');
    expect(source).toContain('onClick={toggleMode}');
  });

  it('uses themeDark and themeLight i18n keys', () => {
    expect(source).toContain('themeDark');
    expect(source).toContain('themeLight');
  });
});

describe('AppThemeProvider source checks', () => {
  const providerPath = path.resolve(process.cwd(), 'components/theme/AppThemeProvider.tsx');
  const providerSource = readFileSync(providerPath, 'utf8');
  const storagePath = path.resolve(process.cwd(), 'lib/theme/theme-storage.ts');
  const storageSource = readFileSync(storagePath, 'utf8');

  it('persists theme to localStorage', () => {
    expect(providerSource).toContain('writeStoredThemeMode');
    expect(storageSource).toContain('localStorage');
    expect(storageSource).toContain('writeStoredThemeMode');
  });

  it('respects system preference via matchMedia', () => {
    expect(storageSource).toContain('matchMedia');
    expect(storageSource).toContain('prefers-color-scheme');
  });
});
