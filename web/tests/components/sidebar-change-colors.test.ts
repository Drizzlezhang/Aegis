import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('sidebar change colors', () => {
  it('uses the shared change-color mapping for watchlist price changes', () => {
    const filePath = path.resolve(process.cwd(), 'components/Sidebar.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain("getChangeColorClasses");
  });
});
