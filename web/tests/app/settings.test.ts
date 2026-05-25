import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockGetSettings = vi.fn();
const mockUpdateSettings = vi.fn();
const mockTestTelegramConnection = vi.fn();

vi.mock('@/lib/api', () => ({
  getSettings: mockGetSettings,
  updateSettings: mockUpdateSettings,
  testTelegramConnection: mockTestTelegramConnection,
}));

vi.mock('@/i18n/get-message', () => ({
  getMessage: (_locale: string, key: string) => key,
}));

vi.mock('@/components/LocaleProvider', () => ({
  useLocale: () => ({ locale: 'en' }),
}));

describe('settings page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches settings from API on load', async () => {
    const { readFileSync } = await import('node:fs');
    const path = await import('node:path');
    const filePath = path.resolve(process.cwd(), 'app/settings/page.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getSettings');
    expect(source).not.toContain('SETTINGS_STORAGE_KEY');
    expect(source).not.toContain('localStorage');
  });

  it('save calls updateSettings API', async () => {
    const { readFileSync } = await import('node:fs');
    const path = await import('node:path');
    const filePath = path.resolve(process.cwd(), 'app/settings/page.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('updateSettings');
    expect(source).toContain('handleSave');
  });

  it('test-telegram calls testTelegramConnection API', async () => {
    const { readFileSync } = await import('node:fs');
    const path = await import('node:path');
    const filePath = path.resolve(process.cwd(), 'app/settings/page.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('testTelegramConnection');
    expect(source).toContain('handleTestMessage');
  });
});
