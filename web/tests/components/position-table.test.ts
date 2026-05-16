import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('position table component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/PositionTable.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('uses MUI table primitives', () => {
    expect(source).toContain('TableContainer');
    expect(source).toContain('<Table size="small">');
    expect(source).toContain('<TableHead>');
    expect(source).toContain('<TableBody>');
  });

  it('sorts active positions first', () => {
    expect(source).toContain("const aRank = a.status === 'active' ? 0 : 1");
    expect(source).toContain("const bRank = b.status === 'active' ? 0 : 1");
  });

  it('uses change-color mapping for pnl and pnl pct', () => {
    expect(source).toContain('getChangeColorClasses(pnlUp).text');
    expect(source).toContain('getChangeColorClasses(pnlPctUp).text');
  });

  it('keeps DTE threshold warnings', () => {
    expect(source).toContain('if (position.dte <= 30)');
    expect(source).toContain("dteColor = 'error'");
    expect(source).toContain('} else if (position.dte <= 60)');
    expect(source).toContain("dteColor = 'warning'");
  });

  it('supports expandable chain rows', () => {
    expect(source).toContain('const toggleRow = async (positionId: string) =>');
    expect(source).toContain('await getPositionChain(positionId)');
    expect(source).toContain('<Collapse in={expanded}');
  });
});
