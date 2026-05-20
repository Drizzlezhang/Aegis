import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('scheduler page', () => {
  const filePath = path.resolve(process.cwd(), 'app/scheduler/page.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders status card with run all button and enable/disabled chip', () => {
    expect(source).toContain('schedulerStatus');
    expect(source).toContain('schedulerRunAll');
    expect(source).toContain('schedulerEnabled');
    expect(source).toContain('schedulerDisabled');
    expect(source).toContain('PlayArrowIcon');
  });

  it('shows unavailable state when backend is unreachable', () => {
    expect(source).toContain('schedulerUnavailable');
    expect(source).toContain('handleAnalyzeSingle');
    expect(source).toContain('schedulerLastResults');
  });
});