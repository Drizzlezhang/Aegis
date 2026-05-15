'use client';

import { Paper, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import type { Locale } from '@/i18n/types';

type DebatePanelProps = {
  debateText: string;
  locale: Locale;
};

type DebateViewModel = {
  bullConfidence: number | null;
  bearConfidence: number | null;
  verdict: string | null;
  verdictConfidence: number | null;
  winningSide: string | null;
  reasoning: string | null;
  bullPoints: string[];
  bearPoints: string[];
};

function parseConfidence(line: string): number | null {
  const match = line.match(/(\d+(?:\.\d+)?)/);
  return match ? Number(match[1]) : null;
}

function parseDebateSection(text: string): DebateViewModel | null {
  if (!text) return null;

  const sectionMatch = text.match(/##\s*Investment\s*Debate([\s\S]*?)(?:\n##\s|$)/i);
  if (!sectionMatch) return null;

  const section = sectionMatch[1].trim();
  if (!section) return null;

  const lines = section
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  let bullConfidence: number | null = null;
  let bearConfidence: number | null = null;
  let verdict: string | null = null;
  let verdictConfidence: number | null = null;
  let winningSide: string | null = null;
  let reasoning: string | null = null;
  const bullPoints: string[] = [];
  const bearPoints: string[] = [];

  let mode: 'bull' | 'bear' | null = null;
  for (const line of lines) {
    const lower = line.toLowerCase();

    if (lower.includes('bull') && lower.includes('confidence')) {
      bullConfidence = parseConfidence(line);
      continue;
    }
    if (lower.includes('bear') && lower.includes('confidence')) {
      bearConfidence = parseConfidence(line);
      continue;
    }
    if (lower.startsWith('verdict')) {
      verdict = line.split(':').slice(1).join(':').trim() || null;
      continue;
    }
    if (lower.includes('winning side')) {
      winningSide = line.split(':').slice(1).join(':').trim() || null;
      continue;
    }
    if (lower.startsWith('rating') || lower.startsWith('confidence')) {
      verdictConfidence = parseConfidence(line);
      continue;
    }
    if (lower.startsWith('reasoning')) {
      reasoning = line.split(':').slice(1).join(':').trim() || null;
      continue;
    }

    if (lower.includes('bull case') || lower.includes('bull points') || lower.startsWith('bull:')) {
      mode = 'bull';
      continue;
    }
    if (lower.includes('bear case') || lower.includes('bear points') || lower.startsWith('bear:')) {
      mode = 'bear';
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const point = line.replace(/^[-*]\s+/, '').trim();
      if (!point) continue;
      if (mode === 'bull') bullPoints.push(point);
      if (mode === 'bear') bearPoints.push(point);
    }
  }

  if (
    !verdict &&
    !winningSide &&
    bullPoints.length === 0 &&
    bearPoints.length === 0 &&
    bullConfidence === null &&
    bearConfidence === null
  ) {
    return null;
  }

  return {
    bullConfidence,
    bearConfidence,
    verdict,
    verdictConfidence,
    winningSide,
    reasoning,
    bullPoints,
    bearPoints,
  };
}

export default function DebatePanel({ debateText, locale }: DebatePanelProps) {
  const parsed = parseDebateSection(debateText);
  if (!parsed) return null;

  return (
    <Paper elevation={0} sx={{ p: 2, borderRadius: '16px', bgcolor: 'action.hover', mb: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
        {getMessage(locale, 'interaction.debate_title')}
      </Typography>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.debate_bull')}
            {parsed.bullConfidence !== null ? ` (${getMessage(locale, 'interaction.debate_confidence')}: ${parsed.bullConfidence})` : ''}
          </Typography>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-500">
            {parsed.bullPoints.map((point, index) => (
              <li key={`bull-${index}`}>{point}</li>
            ))}
          </ul>
        </div>

        <div>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.debate_bear')}
            {parsed.bearConfidence !== null ? ` (${getMessage(locale, 'interaction.debate_confidence')}: ${parsed.bearConfidence})` : ''}
          </Typography>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-500">
            {parsed.bearPoints.map((point, index) => (
              <li key={`bear-${index}`}>{point}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-2 space-y-1 text-xs text-slate-500">
        {parsed.verdict && (
          <div>
            <span className="font-semibold text-[var(--foreground)]">{getMessage(locale, 'interaction.debate_verdict')}:</span> {parsed.verdict}
            {parsed.verdictConfidence !== null ? ` (${getMessage(locale, 'interaction.debate_confidence')}: ${parsed.verdictConfidence})` : ''}
          </div>
        )}
        {parsed.winningSide && (
          <div>
            <span className="font-semibold text-[var(--foreground)]">{getMessage(locale, 'interaction.debate_winning_side')}:</span> {parsed.winningSide}
          </div>
        )}
        {parsed.reasoning && <div>{parsed.reasoning}</div>}
      </div>
    </Paper>
  );
}
