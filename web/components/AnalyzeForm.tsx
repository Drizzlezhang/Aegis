'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Chip, Paper, Stack, Typography } from '@mui/material';
import type { AnalysisRecommendation, AnalysisResult } from '@/lib/api';
import { getMessage } from '@/i18n/get-message';
import { interpolate } from '@/i18n/interpolate';
import AnalysisProgress, { type AnalysisProgressCompletePayload } from './AnalysisProgress';
import DebatePanel from './DebatePanel';
import { useLocale } from './LocaleProvider';
import SymbolSearch from './SymbolSearch';

type ViewMode = 'idle' | 'progress' | 'results';

function RecommendationCard({ rec, locale }: { rec: AnalysisRecommendation; locale: 'zh-CN' | 'en' }) {
  return (
    <Paper elevation={0} sx={{ p: 2, borderRadius: '20px', bgcolor: 'action.hover' }}>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-[var(--foreground)]">{rec.type}</span>
          <Chip
            label={`${Math.round(rec.confidence * 100)}% ${getMessage(locale, 'interaction.results_confidence')}`}
            size="small"
            variant="outlined"
          />
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
          <div>Contract: <span className="text-[var(--foreground)]">{rec.contractSymbol}</span></div>
          <div>Strike: <span className="text-[var(--foreground)]">${rec.strike}</span></div>
          <div>Expiry: <span className="text-[var(--foreground)]">{rec.expiry}</span></div>
          <div>Entry: <span className="text-[var(--foreground)]">${rec.entryPrice}</span></div>
          {rec.targetPrice !== null && (
            <div>Target: <span className="text-emerald-500">${rec.targetPrice}</span></div>
          )}
          {rec.stopLoss !== null && (
            <div>Stop: <span className="text-rose-500">${rec.stopLoss}</span></div>
          )}
          {rec.riskRewardRatio !== null && (
            <div>
              {getMessage(locale, 'interaction.results_risk_reward')}: <span className="text-[var(--foreground)]">{rec.riskRewardRatio.toFixed(2)}</span>
            </div>
          )}
        </div>
        <p className="text-xs leading-relaxed text-slate-500">{rec.reasoning}</p>
      </div>
    </Paper>
  );
}

export default function AnalyzeForm() {
  const { locale } = useLocale();
  const [selected, setSelected] = useState<string[]>([]);
  const [analyzingSymbols, setAnalyzingSymbols] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('idle');
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [error, setError] = useState('');

  const running = viewMode === 'progress';

  const handleAnalyze = () => {
    if (selected.length === 0) {
      setError(getMessage(locale, 'interaction.analyze_no_selection'));
      return;
    }

    setAnalyzingSymbols(selected);
    setViewMode('progress');
    setResults([]);
    setError('');
  };

  const handleComplete = (payload: AnalysisProgressCompletePayload) => {
    setResults(payload.results);
    setError('');
    setViewMode('results');
  };

  const handleError = (message: string) => {
    setError(message);
  };

  return (
    <div className="space-y-4">
      <SymbolSearch selected={selected} onChange={setSelected} disabled={running} />

      <Button
        onClick={handleAnalyze}
        disabled={running || selected.length === 0}
        variant="contained"
        size="large"
        fullWidth
        sx={{ borderRadius: '18px', py: 1.4, fontWeight: 700 }}
      >
        {running
          ? getMessage(locale, 'interaction.status_running')
          : interpolate(getMessage(locale, 'interaction.analyze_button'), { count: selected.length })}
      </Button>

      {viewMode === 'progress' && analyzingSymbols.length > 0 && (
        <AnalysisProgress
          symbols={analyzingSymbols}
          onComplete={handleComplete}
          onError={handleError}
          autoStart
        />
      )}

      {error && (
        <Paper elevation={0} className="card">
          <Typography variant="body2" sx={{ color: 'error.main' }}>
            {getMessage(locale, 'common.error')}: {error}
          </Typography>
        </Paper>
      )}

      {results.length > 0 && (
        <div className="space-y-4">
          {results.map((result) => (
            <Paper key={result.symbol} elevation={0} className="card">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`h-2.5 w-2.5 rounded-full ${result.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  <span className="font-semibold text-[var(--foreground)]">{result.symbol}</span>
                  <span className="text-xs text-slate-500">{result.recommendationsCount} {getMessage(locale, 'interaction.results_title')}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{result.agentSequence.length} {getMessage(locale, 'interaction.agents')}</span>
                  {result.status === 'success' && (
                    <Link href={`/symbol/${result.symbol}`} className="text-xs font-semibold text-[color:#6750A4] hover:opacity-80">
                      {getMessage(locale, 'interaction.results_view_detail')} →
                    </Link>
                  )}
                </div>
              </div>

              <DebatePanel debateText={result.report} locale={locale} />

              {result.report && (
                <p className="mb-3 whitespace-pre-line text-xs leading-relaxed text-slate-500">
                  {result.report}
                </p>
              )}

              {result.recommendations.length > 0 ? (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {getMessage(locale, 'interaction.results_title')}
                  </h4>
                  <Stack spacing={2}>
                    {result.recommendations.map((rec, idx) => (
                      <RecommendationCard key={`${result.symbol}-${idx}`} rec={rec} locale={locale} />
                    ))}
                  </Stack>
                </div>
              ) : (
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {getMessage(locale, 'interaction.results_no_recommendations')}
                </Typography>
              )}
            </Paper>
          ))}
        </div>
      )}
    </div>
  );
}
