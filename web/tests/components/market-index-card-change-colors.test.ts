import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('market index card change colors', () => {
  it('uses the shared change-color mapping for market direction colors', () => {
    const filePath = path.resolve(process.cwd(), 'components/market-index-card.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getChangeColorClasses');
  });
});
