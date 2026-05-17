import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('RealtimeTicker component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/RealtimeTicker.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders symbols list and uses useWebSocket', () => {
    expect(source).toContain('export function RealtimeTicker');
    expect(source).toContain('useWebSocket');
    expect(source).toContain('symbols.map');
  });

  it('shows connection status indicator', () => {
    expect(source).toContain('statusLabel');
    expect(source).toContain('statusColor');
    expect(source).toContain("borderRadius: '50%'");
    expect(source).toContain('pulse 1.5s infinite');
  });

  it('updates price on message and flashes background', () => {
    expect(source).toContain('setPrices');
    expect(source).toContain('setFlashSymbol');
    expect(source).toContain('isFlashing');
    expect(source).toContain("transition: 'background-color 0.3s'");
  });

  it('uses China market color convention (up red, down green)', () => {
    expect(source).toContain("color={isUp ? 'error.main' : 'success.main'}");
  });
});
