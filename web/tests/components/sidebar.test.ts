import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('sidebar component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/Sidebar.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('includes positions navigation entry', () => {
    expect(source).toContain("{ href: '/positions', key: 'common.positions' as const }");
  });

  it('uses i18n key rendering for nav labels', () => {
    expect(source).toContain('getMessage(locale, item.key)');
  });
});
