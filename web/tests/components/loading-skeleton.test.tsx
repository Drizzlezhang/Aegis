import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('LoadingSkeleton component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/LoadingSkeleton.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders page variant', () => {
    expect(source).toContain("variant = 'page'");
    expect(source).toContain('loading-skeleton-page');
  });

  it('renders table rows based on rows prop', () => {
    expect(source).toContain("case 'table'");
    expect(source).toContain('Array.from({ length: rows })');
    expect(source).toContain('loading-skeleton-row');
  });
});
