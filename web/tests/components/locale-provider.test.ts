import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('locale provider hydration behavior', () => {
  it('does not update locale in a mount-only effect after first render', () => {
    const filePath = path.resolve(process.cwd(), 'components/LocaleProvider.tsx');
    const source = readFileSync(filePath, 'utf8');

    expect(source).not.toContain("setLocale(readStoredLocale(initialLocale))");
  });
});
