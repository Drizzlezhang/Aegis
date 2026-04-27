import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('market sentiment banner change colors', () => {
  it('uses the shared change-color mapping for index changes', () => {
    const filePath = path.resolve(process.cwd(), 'components/market-sentiment-banner.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getChangeColorClasses');
  });
});
