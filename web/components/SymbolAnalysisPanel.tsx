'use client';

import { useState } from 'react';
import { runAnalysis, type AnalysisResult, type AnalysisRecommendation } from '@/lib/api';

function RecommendationCard({ rec }: { rec: AnalysisRecommendation }) {
  return (
    <div className="rounded-lg bg-slate-800/50 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-200">{rec.type}</span>
        <span className="text-xs rounded-full bg-slate-700 px-2 py-0.5 text-slate-300">
          {Math.round(rec.confidence * 100)}% confidence
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-400">
        <div>Contract: <span className="text-slate-200">{rec.contractSymbol}</span></div>
        <div>Strike: <span className="text-slate-200">${rec.strike}</span></div>
        <div>Expiry: <span className="text-slate-200">{rec.expiry}</span></div>
        <div>Entry: <span className="text-slate-200">${rec.entryPrice}</span></div>
        {rec.targetPrice !== null && (
          <div>Target: <span className="text-emerald-400">${rec.targetPrice}</span></div>
        )}
        {rec.stopLoss !== null && (
          <div>Stop: <span className="text-rose-400">${rec.stopLoss}</span></div>
        )}
        {rec.riskRewardRatio !== null && (
          <div>R/R: <span className="text-slate-200">{rec.riskRewardRatio.toFixed(2)}</span></div>
        )}
      </div>
      <p className="text-xs text-slate-500 leading-relaxed">{rec.reasoning}</p>
    </div>
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

      // Animate progress for UX
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
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">Multi-Agent Analysis</h3>
        <button
          onClick={handleAnalyze}
          disabled={running}
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
        >
          {running ? 'Running...' : 'Run Analysis'}
        </button>
      </div>

      {error && (
        <p className="text-sm text-rose-400">Error: {error}</p>
      )}

      {running && (
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-300">{currentStep}</span>
            <span className="text-slate-500">{Math.round(progress)}%</span>
          </div>
          <div className="mt-2 h-2 w-full rounded-full bg-slate-800">
            <div
              className="h-2 rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Agent Sequence */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">Agents:</span>
            {result.agentSequence.map((agent, idx) => (
              <span key={agent} className="flex items-center gap-1 text-xs">
                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">{agent}</span>
                {idx < result.agentSequence.length - 1 && (
                  <span className="text-slate-600">→</span>
                )}
              </span>
            ))}
          </div>

          {/* Status */}
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                result.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            />
            <span className="text-xs text-slate-400 capitalize">{result.status}</span>
            <span className="text-xs text-slate-500">
              {result.recommendationsCount} recommendations
            </span>
          </div>

          {/* Report */}
          {result.report && (
            <div className="rounded-lg bg-slate-800/30 p-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Agent Report
              </h4>
              <pre className="text-xs text-slate-400 leading-relaxed whitespace-pre-wrap font-mono">
                {result.report}
              </pre>
            </div>
          )}

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Strategy Recommendations
              </h4>
              {result.recommendations.map((rec, idx) => (
                <RecommendationCard key={`${symbol}-${idx}`} rec={rec} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
