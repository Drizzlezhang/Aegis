import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('analysis panel dependencies', () => {
  it('does not depend on removed mock-data module', () => {
    const filePath = path.resolve(process.cwd(), 'components/AnalysisPanel.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).not.toContain("@/lib/mock-data");
  });
});
