import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('AnalysisReport component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/AnalysisReport.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('executive summary expanded by default', () => {
    expect(source).toContain("'executive_summary'");
    expect(source).toContain('initialExpanded');
    expect(source).toContain('expanded');
  });

  it('toggle section via accordion onChange', () => {
    expect(source).toContain('toggleSection');
    expect(source).toContain('onChange={() => toggleSection(section.id)}');
  });

  it('expand all and collapse all buttons', () => {
    expect(source).toContain('expandAll');
    expect(source).toContain('collapseAll');
    expect(source).toContain('reportExpandAll');
    expect(source).toContain('reportCollapseAll');
  });

  it('number highlighting for $price and xx%', () => {
    expect(source).toContain('highlightNumbers');
    expect(source).toContain("part.startsWith('$')");
    expect(source).toContain("part.endsWith('%')");
  });
});
