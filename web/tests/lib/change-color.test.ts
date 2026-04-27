import { describe, expect, it } from 'vitest';
import { getChangeColorClasses } from '@/lib/change-color';

describe('getChangeColorClasses', () => {
  it('maps gains to red and losses to green', () => {
    expect(getChangeColorClasses(true)).toEqual({
      text: 'text-rose-400',
      bg: 'bg-rose-500/10',
      solid: 'bg-rose-500',
    });

    expect(getChangeColorClasses(false)).toEqual({
      text: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      solid: 'bg-emerald-500',
    });
  });
});
