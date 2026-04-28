'use client';

import { useState } from 'react';
import { Button, Chip, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import { runAnalysis, type AnalysisResult, type AnalysisRecommendation } from '@/lib/api';

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
        <p className="text-xs text-slate-500 leading-relaxed">{rec.reasoning}</p>
      </div>
    </Paper>
  );
}

interface SymbolAnalysisPanelProps {
  symbol: string;
}

export default function SymbolAnalysisPanel({ symbol }: SymbolAnalysisPanelProps) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState('');

  const handleAnalyze = async () => {
    setRunning(true);
    setProgress(0);
    setResult(null);
    setError('');
    setCurrentStep('Initiating analysis...');

    try {
      const data = await runAnalysis([symbol]);

      for (let i = 0; i <= 100; i += 10) {
        setProgress(i);
        setCurrentStep(`Processing... ${i}%`);
        await new Promise((r) => setTimeout(r, 150));
      }

      setResult(data.results[0] || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setRunning(false);
      setProgress(0);
      setCurrentStep('');
    }
  };

  return (
    <Paper elevation={0} className="card">
      <div className="flex items-center justify-between gap-3">
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
          Multi-Agent Analysis
        </Typography>
        <Button
          onClick={handleAnalyze}
          disabled={running}
          variant="contained"
          sx={{ borderRadius: '16px', fontWeight: 700 }}
        >
          {running ? 'Running...' : 'Run Analysis'}
        </Button>
      </div>

      {error && (
        <Typography variant="body2" sx={{ mt: 2, color: 'error.main' }}>
          Error: {error}
        </Typography>
      )}

      {running && (
        <div className="mt-3">
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
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">Agents:</span>
            {result.agentSequence.map((agent, idx) => (
              <span key={agent} className="flex items-center gap-1 text-xs">
                <Chip label={agent} size="small" variant="outlined" />
                {idx < result.agentSequence.length - 1 && <span className="text-slate-600">→</span>}
              </span>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                result.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            />
            <span className="text-xs capitalize text-slate-500">{result.status}</span>
            <span className="text-xs text-slate-500">
              {result.recommendationsCount} recommendations
            </span>
          </div>

          {result.report && (
            <Paper elevation={0} className="card-muted">
              <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Agent Report
              </Typography>
              <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-500 font-mono">
                {result.report}
              </pre>
            </Paper>
          )}

          {result.recommendations.length > 0 && (
            <div className="space-y-2">
              <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Strategy Recommendations
              </Typography>
              <Stack spacing={2} sx={{ mt: 1 }}>
                {result.recommendations.map((rec, idx) => (
                  <RecommendationCard key={`${symbol}-${idx}`} rec={rec} />
                ))}
              </Stack>
            </div>
          )}
        </div>
      )}
    </Paper>
  );
}
