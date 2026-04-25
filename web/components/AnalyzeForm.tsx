'use client';

import { useState } from 'react';
import Link from 'next/link';

const SYMBOLS = ['QQQ', 'SPY', 'NVDA', 'MSFT', 'AAPL', 'PLTR', 'NFLX', 'INTC', 'TSM', 'TSLA', 'KO'];

interface AnalysisResult {
  symbol: string;
  status: string;
  agentSequence: string[];
  recommendationsCount: number;
  executionTime: number;
  report: string;
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
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    );
  };

  const runAnalysis = async () => {
    if (selected.length === 0) return;

    setRunning(true);
    setProgress(0);
    setResults([]);
    setError('');
    setCurrentStep('Initiating analysis...');

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: selected }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(errData.detail || `Request failed: ${res.status}`);
      }

      const data = await res.json();
      const results: AnalysisResult[] = data.results || [];

      // Animate progress for UX
      for (let i = 0; i <= 100; i += 10) {
        setProgress(i);
        setCurrentStep(`Processing... ${i}%`);
        await new Promise((r) => setTimeout(r, 150));
      }

      setResults(results);
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
      {/* Symbol Selection */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-slate-300">Select Symbols</h3>
        <div className="flex flex-wrap gap-2">
          {SYMBOLS.map((sym) => {
            const active = selected.includes(sym);
            return (
              <button
                key={sym}
                onClick={() => toggleSymbol(sym)}
                disabled={running}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-950 text-blue-300 ring-1 ring-blue-800'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                } disabled:opacity-50`}
              >
                {sym}
              </button>
            );
          })}
        </div>
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            {selected.length} symbol{selected.length !== 1 ? 's' : ''} selected
          </p>
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              disabled={running}
              className="text-xs text-slate-500 hover:text-slate-300 disabled:opacity-50"
            >
              Clear all
            </button>
          )}
        </div>
      </div>

      {/* Run Button */}
      <button
        onClick={runAnalysis}
        disabled={running || selected.length === 0}
        className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
      >
        {running ? 'Running Analysis...' : `Analyze ${selected.length > 0 ? selected.length + ' Symbol' + (selected.length > 1 ? 's' : '') : ''}`}
      </button>

      {/* Error */}
      {error && (
        <div className="card">
          <p className="text-sm text-rose-400">Error: {error}</p>
        </div>
      )}

      {/* Progress */}
      {running && (
        <div className="card">
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

      {/* Results */}
      {results.length > 0 && (
        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">Results</h3>
          <div className="space-y-2">
            {results.map((result) => (
              <div
                key={result.symbol}
                className="flex items-center justify-between rounded-lg bg-slate-800/50 p-3"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      result.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                  />
                  <span className="font-medium text-slate-200">{result.symbol}</span>
                  <span className="text-xs text-slate-500">
                    {result.recommendationsCount} recommendations
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{result.agentSequence.length} agents</span>
                  {result.status === 'success' && (
                    <Link
                      href={`/symbol/${result.symbol}`}
                      className="text-xs font-medium text-blue-400 hover:text-blue-300"
                    >
                      View →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
