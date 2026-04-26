'use client';

import { useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { runBacktest } from '@/lib/api';

interface BacktestConfig {
  symbol: string;
  strategy: 'leaps_call' | 'bull_spread' | 'covered_call';
  signalType: 'sma_crossover' | 'rsi' | 'sma_rsi_combo';
  startDate: string;
  endDate: string;
  initialCapital: number;
  rsiPeriod: number;
  rsiOverbought: number;
  rsiOversold: number;
}

interface Trade {
  date: string;
  type: 'entry' | 'exit';
  price: number;
  pnl: number | null;
  pnlPercent: number | null;
}

interface BacktestResult {
  equityCurve: { date: string; value: number; benchmark: number }[];
  trades: Trade[];
  metrics: {
    totalReturn: number;
    annualizedReturn: number;
    winRate: number;
    profitFactor: number;
    maxDrawdown: number;
    sharpeRatio: number;
    totalTrades: number;
    avgWin: number;
    avgLoss: number;
    bestTrade: number;
    worstTrade: number;
  };
  monthlyReturns: { month: string; return: number }[];
}

function MetricCard({ label, value, suffix = '', color = 'text-slate-200' }: { label: string; value: string | number; suffix?: string; color?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${color}`}>
        {typeof value === 'number' ? value.toFixed(2) : value}
        {suffix}
      </p>
    </div>
  );
}

export default function BacktestPageContent() {
  const [config, setConfig] = useState<BacktestConfig>({
    symbol: 'QQQ',
    strategy: 'bull_spread',
    signalType: 'sma_crossover',
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    initialCapital: 100000,
    rsiPeriod: 14,
    rsiOverbought: 70,
    rsiOversold: 30,
  });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiResult = await runBacktest({
        symbol: config.symbol,
        start_date: config.startDate,
        end_date: config.endDate,
        initial_capital: config.initialCapital,
        strategy: config.strategy,
        signal_type: config.signalType,
        rsi_period: config.rsiPeriod,
        rsi_overbought: config.rsiOverbought,
        rsi_oversold: config.rsiOversold,
      });
      setResult({
        equityCurve: apiResult.equityCurve,
        trades: apiResult.trades,
        metrics: apiResult.metrics,
        monthlyReturns: apiResult.monthlyReturns,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backtest failed');
    } finally {
      setLoading(false);
    }
  };

  const strategyNames: Record<string, string> = {
    leaps_call: 'LEAPS Call',
    bull_spread: 'Bull Spread',
    covered_call: 'Covered Call',
  };

  const signalTypeNames: Record<string, string> = {
    sma_crossover: 'SMA Crossover',
    rsi: 'RSI',
    sma_rsi_combo: 'SMA + RSI Combo',
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Strategy Backtest</h1>
        <p className="mt-1 text-sm text-slate-500">Simulate historical performance of options strategies</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-300">Configuration</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Symbol</label>
            <select
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
              value={config.symbol}
              onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
            >
              {['QQQ', 'SPY', 'NVDA', 'AAPL', 'TSLA', 'MSFT', 'PLTR'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Strategy</label>
            <select
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
              value={config.strategy}
              onChange={(e) => setConfig({ ...config, strategy: e.target.value as BacktestConfig['strategy'] })}
            >
              <option value="leaps_call">LEAPS Call</option>
              <option value="bull_spread">Bull Spread</option>
              <option value="covered_call">Covered Call</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Signal Type</label>
            <select
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
              value={config.signalType}
              onChange={(e) => setConfig({ ...config, signalType: e.target.value as BacktestConfig['signalType'] })}
            >
              <option value="sma_crossover">SMA Crossover</option>
              <option value="rsi">RSI</option>
              <option value="sma_rsi_combo">SMA + RSI Combo</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Start Date</label>
            <input type="date" className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200" value={config.startDate} onChange={(e) => setConfig({ ...config, startDate: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">End Date</label>
            <input type="date" className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200" value={config.endDate} onChange={(e) => setConfig({ ...config, endDate: e.target.value })} />
          </div>
          <div className="flex items-end">
            <button onClick={handleRunBacktest} disabled={loading} className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? 'Running...' : 'Run Backtest'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-800 bg-rose-900/30 p-4 text-sm text-rose-300">{error}</div>}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <MetricCard label="Total Return" value={result.metrics.totalReturn} suffix="%" color={result.metrics.totalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'} />
            <MetricCard label="Annualized" value={result.metrics.annualizedReturn} suffix="%" />
            <MetricCard label="Win Rate" value={result.metrics.winRate} suffix="%" />
            <MetricCard label="Profit Factor" value={result.metrics.profitFactor} />
            <MetricCard label="Max Drawdown" value={result.metrics.maxDrawdown} suffix="%" color="text-rose-400" />
            <MetricCard label="Sharpe Ratio" value={result.metrics.sharpeRatio} />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h3 className="mb-4 text-sm font-semibold text-slate-300">
              Equity Curve — {config.symbol} {strategyNames[config.strategy]} ({signalTypeNames[config.signalType]})
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={result.equityCurve} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} interval={Math.floor(result.equityCurve.length / 8)} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`} width={50} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(value: unknown) => {
                    const num = typeof value === 'number' ? value : Number(value);
                    return [`$${num.toFixed(0)}`, ''];
                  }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill="url(#equityGradient)" dot={false} name="Strategy" />
                <Line type="monotone" dataKey="benchmark" stroke="#475569" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Buy & Hold" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-4 text-sm font-semibold text-slate-300">Monthly Returns</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={result.monthlyReturns} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="month" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={40} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(value: unknown) => {
                      const num = typeof value === 'number' ? value : Number(value);
                      return [`${num.toFixed(2)}%`, 'Return'];
                    }}
                  />
                  <Bar dataKey="return" radius={[4, 4, 0, 0]}>
                    {result.monthlyReturns.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.return >= 0 ? '#10b981' : '#f43f5e'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-4 text-sm font-semibold text-slate-300">Trade Statistics</h3>
              <div className="space-y-3">
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Total Trades</span><span className="text-sm font-medium text-slate-200">{result.metrics.totalTrades}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Winning Trades</span><span className="text-sm font-medium text-emerald-400">{Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100))}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Losing Trades</span><span className="text-sm font-medium text-rose-400">{result.metrics.totalTrades - Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100))}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Average Win</span><span className="text-sm font-medium text-emerald-400">${result.metrics.avgWin.toFixed(0)}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Average Loss</span><span className="text-sm font-medium text-rose-400">${result.metrics.avgLoss.toFixed(0)}</span></div>
                <div className="flex justify-between border-b border-slate-800 pb-2"><span className="text-xs text-slate-500">Best Trade</span><span className="text-sm font-medium text-emerald-400">+{result.metrics.bestTrade.toFixed(2)}%</span></div>
                <div className="flex justify-between"><span className="text-xs text-slate-500">Worst Trade</span><span className="text-sm font-medium text-rose-400">{result.metrics.worstTrade.toFixed(2)}%</span></div>
              </div>
            </div>
          </div>

          {result.trades.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="mb-4 text-sm font-semibold text-slate-300">Trade History</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left">
                      <th className="pb-2 text-xs font-medium text-slate-500">Date</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">Price</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">P&L</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(0, 10).map((trade, i) => (
                      <tr key={i} className="border-b border-slate-800/50">
                        <td className="py-2 text-slate-300">{trade.date}</td>
                        <td className="py-2 text-slate-300">${trade.price.toFixed(2)}</td>
                        <td className={`py-2 ${(trade.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{(trade.pnl || 0) >= 0 ? '+' : ''}${(trade.pnl || 0).toFixed(0)}</td>
                        <td className={`py-2 ${(trade.pnlPercent || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{(trade.pnlPercent || 0) >= 0 ? '+' : ''}{(trade.pnlPercent || 0).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {result.trades.length > 10 && <p className="mt-2 text-xs text-slate-500">Showing 10 of {result.trades.length} trades</p>}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
