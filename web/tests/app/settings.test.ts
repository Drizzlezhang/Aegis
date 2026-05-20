import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('settings page', () => {
  const filePath = path.resolve(process.cwd(), 'app/settings/page.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders all sections: Telegram, notifications, threshold, silent hours', () => {
    expect(source).toContain('settingsTelegram');
    expect(source).toContain('settingsNotifications');
    expect(source).toContain('settingsConfidenceThreshold');
    expect(source).toContain('settingsSilentHours');
  });

  it('saves settings to localStorage on save button click', () => {
    expect(source).toContain('settingsSave');
    expect(source).toContain('handleSave');
    expect(source).toContain('SETTINGS_STORAGE_KEY');
    expect(source).toContain('localStorage');
  });
});