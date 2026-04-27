import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('backtest page change colors', () => {
  it('uses the shared change-color mapping for return and pnl displays', () => {
    const filePath = path.resolve(process.cwd(), 'components/BacktestPageContent.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getChangeColorClasses');
  });
});
