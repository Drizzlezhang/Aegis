import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('symbol card change colors', () => {
  it('uses the shared change-color mapping for price changes and trend direction', () => {
    const filePath = path.resolve(process.cwd(), 'components/SymbolCard.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain('getChangeColorClasses');
  });
});
