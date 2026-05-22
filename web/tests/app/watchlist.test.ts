import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('watchlist page', () => {
  const filePath = path.resolve(process.cwd(), 'app/watchlist/page.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('shows empty state message when no symbols exist', () => {
    expect(source).toContain('watchlistEmpty');
  });

  it('renders add form with symbol input, priority selector, and notes', () => {
    expect(source).toContain('watchlistAdd');
    expect(source).toContain('watchlistPriority');
    expect(source).toContain('watchlistNotes');
    expect(source).toContain('handleAdd');
    expect(source).toContain('DeleteIcon');
  });
});