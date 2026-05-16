import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('alerts panel component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/AlertsPanel.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('loads alerts from API helper', () => {
    expect(source).toContain('const resp = await getPositionAlerts()');
  });

  it('keeps 30s polling with cleanup', () => {
    expect(source).toContain('const timer = setInterval(() =>');
    expect(source).toContain('}, 30000);');
    expect(source).toContain('clearInterval(timer)');
  });

  it('sorts by severity rank critical->warning->info', () => {
    expect(source).toContain('critical: 0');
    expect(source).toContain('warning: 1');
    expect(source).toContain('info: 2');
    expect(source).toContain('severityRank[a.severity]');
  });

  it('keeps loading and empty states with i18n keys', () => {
    expect(source).toContain("getMessage(locale, 'interaction.alerts_loading')");
    expect(source).toContain("getMessage(locale, 'interaction.alerts_empty')");
    expect(source).toContain("getMessage(locale, 'interaction.alerts_last_scanned')");
  });
});
