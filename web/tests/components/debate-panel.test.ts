import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('debate panel component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/DebatePanel.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('parses investment debate section', () => {
    expect(source).toContain('function parseDebateSection(text: string): DebateViewModel | null');
    expect(source).toContain('/##\\s*Investment\\s*Debate([\\s\\S]*?)(?:\\n##\\s|$)/i');
    expect(source).toContain("if (!parsed) return null");
  });

  it('extracts bull bear verdict fields', () => {
    expect(source).toContain("let mode: 'bull' | 'bear' | null = null");
    expect(source).toContain('bullPoints.push(point)');
    expect(source).toContain('bearPoints.push(point)');
    expect(source).toContain('parsed.verdict');
    expect(source).toContain('parsed.winningSide');
  });

  it('uses i18n keys for labels', () => {
    expect(source).toContain("'interaction.debate_title'");
    expect(source).toContain("'interaction.debate_bull'");
    expect(source).toContain("'interaction.debate_bear'");
    expect(source).toContain("'interaction.debate_verdict'");
  });
});
