'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Chip, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import { runAnalysis, type AnalysisResult, type AnalysisRecommendation } from '@/lib/api';

const SYMBOLS = ['QQQ', 'SPY', 'NVDA', 'MSFT', 'AAPL', 'PLTR', 'NFLX', 'INTC', 'TSM', 'TSLA', 'KO'];

function RecommendationCard({ rec }: { rec: AnalysisRecommendation }) {
  return (
    <Paper elevation={0} sx={{ p: 2, borderRadius: '20px', bgcolor: 'action.hover' }}>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-[var(--foreground)]">{rec.type}</span>
          <Chip label={`${Math.round(rec.confidence * 100)}% confidence`} size="small" variant="outlined" />
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
            <div>R/R: <span className="text-[var(--foreground)]">{rec.riskRewardRatio.toFixed(2)}</span></div>
          )}
        </div>
        <p className="text-xs leading-relaxed text-slate-500">{rec.reasoning}</p>
      </div>
    </Paper>
  );
}

export default function AnalyzeForm() {
  const [selected, setSelected] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [error, setError] = useState('');

  const toggleSymbol = (sym: string) => {
    setSelected((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym],
    );
  };

  const handleAnalyze = async () => {
    if (selected.length === 0) return;

    setRunning(true);
    setProgress(0);
    setResults([]);
    setError('');
    setCurrentStep('Initiating analysis...');

    try {
      const data = await runAnalysis(selected);

      for (let i = 0; i <= 100; i += 10) {
        setProgress(i);
        setCurrentStep(`Processing... ${i}%`);
        await new Promise((r) => setTimeout(r, 150));
      }

      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setRunning(false);
      setProgress(0);
      setCurrentStep('');
    }
  };

  return (
    <div className="space-y-4">
      <Paper elevation={0} className="card">
        <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
          Select Symbols
        </Typography>
        <div className="flex flex-wrap gap-2">
          {SYMBOLS.map((sym) => {
            const active = selected.includes(sym);
            return (
              <Button
                key={sym}
                onClick={() => toggleSymbol(sym)}
                disabled={running}
                variant={active ? 'contained' : 'outlined'}
                color={active ? 'primary' : 'inherit'}
                sx={{ borderRadius: '999px', minWidth: 0, px: 2 }}
              >
                {sym}
              </Button>
            );
          })}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {selected.length} symbol{selected.length !== 1 ? 's' : ''} selected
          </Typography>
          {selected.length > 0 && (
            <Button onClick={() => setSelected([])} disabled={running} size="small">
              Clear all
            </Button>
          )}
        </div>
      </Paper>

      <Button
        onClick={handleAnalyze}
        disabled={running || selected.length === 0}
        variant="contained"
        size="large"
        fullWidth
        sx={{ borderRadius: '18px', py: 1.4, fontWeight: 700 }}
      >
        {running ? 'Running Analysis...' : `Analyze ${selected.length > 0 ? selected.length + ' Symbol' + (selected.length > 1 ? 's' : '') : ''}`}
      </Button>

      {error && (
        <Paper elevation={0} className="card">
          <Typography variant="body2" sx={{ color: 'error.main' }}>Error: {error}</Typography>
        </Paper>
      )}

      {running && (
        <Paper elevation={0} className="card">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--foreground)]">{currentStep}</span>
            <span className="text-slate-500">{Math.round(progress)}%</span>
          </div>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              mt: 2,
              height: 10,
              borderRadius: 999,
              bgcolor: 'action.hover',
              '& .MuiLinearProgress-bar': {
                borderRadius: 999,
              },
            }}
          />
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
                  <span className="text-xs text-slate-500">{result.recommendationsCount} recommendations</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{result.agentSequence.length} agents</span>
                  {result.status === 'success' && (
                    <Link href={`/symbol/${result.symbol}`} className="text-xs font-semibold text-[color:#6750A4] hover:opacity-80">
                      View →
                    </Link>
                  )}
                </div>
              </div>

              {result.report && (
                <p className="mb-3 whitespace-pre-line text-xs leading-relaxed text-slate-500">
                  {result.report}
                </p>
              )}

              {result.recommendations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Strategy Recommendations
                  </h4>
                  <Stack spacing={2}>
                    {result.recommendations.map((rec, idx) => (
                      <RecommendationCard key={`${result.symbol}-${idx}`} rec={rec} />
                    ))}
                  </Stack>
                </div>
              )}
            </Paper>
          ))}
        </div>
      )}
    </div>
  );
}
