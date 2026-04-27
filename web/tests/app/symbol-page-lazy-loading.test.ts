import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('symbol page lazy loading', () => {
  it('loads SymbolAnalysisPanel with next/dynamic instead of static import', () => {
    const filePath = path.resolve(process.cwd(), 'app/symbol/[symbol]/page.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain("import dynamic from 'next/dynamic'");
    expect(source).toContain("dynamic(() => import('@/components/SymbolAnalysisPanel')");
    expect(source).not.toContain("import SymbolAnalysisPanel from '@/components/SymbolAnalysisPanel'");
  });

  it('uses the shared change-color mapping for the price change', () => {
    const filePath = path.resolve(process.cwd(), 'app/symbol/[symbol]/page.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).toContain("import { getChangeColorClasses } from '@/lib/change-color'");
    expect(source).toContain('const changeColors = getChangeColorClasses(positive);');
    expect(source).toContain('changeColors.text');
  });
});
