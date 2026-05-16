import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('symbol search component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/SymbolSearch.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('defines popular symbols list', () => {
    expect(source).toContain("const POPULAR_SYMBOLS = ['QQQ', 'SPY', 'NVDA', 'MSFT', 'AAPL', 'PLTR', 'NFLX', 'INTC', 'TSM', 'TSLA', 'KO']");
  });

  it('normalizes symbols and tokenizes by comma', () => {
    expect(source).toContain('function normalizeSymbol(raw: string): string');
    expect(source).toContain('return raw.trim().toUpperCase()');
    expect(source).toContain(".split(',')");
  });

  it('enforces dedupe and maxSymbols constraints', () => {
    expect(source).toContain('maxSymbols = 20');
    expect(source).toContain('if (next.length >= maxSymbols) break');
    expect(source).toContain('!selectedSet.has(symbol) && !next.includes(symbol)');
    expect(source).toContain("getMessage(locale, 'interaction.symbol_search_max_reached')");
  });
});
