import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('market sentiment inline change colors', () => {
  it('uses the shared change-color mapping for inline index changes', () => {
    const filePath = path.resolve(process.cwd(), 'components/market-sentiment-inline.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getChangeColorClasses');
  });
});
