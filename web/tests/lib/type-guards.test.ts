import { describe, expect, it } from 'vitest';
import { isStructuredReport } from '@/lib/type-guards';

describe('isStructuredReport', () => {
  it('accepts non-null objects with sections array', () => {
    expect(isStructuredReport({ sections: [] })).toBe(true);
    expect(isStructuredReport({ sections: [{ id: 'executive_summary' }] })).toBe(true);
  });

  it('rejects invalid values', () => {
    expect(isStructuredReport(null)).toBe(false);
    expect(isStructuredReport(undefined)).toBe(false);
    expect(isStructuredReport('report')).toBe(false);
    expect(isStructuredReport({})).toBe(false);
    expect(isStructuredReport({ sections: 'not-array' })).toBe(false);
  });
});
