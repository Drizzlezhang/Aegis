'use client';

import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';

interface BacktestConfig {
  symbol: string;
  strategy: 'leaps_call' | 'bull_spread' | 'covered_call';
  startDate: string;
  endDate: string;
  initialCapital: number;
}

interface Trade {
  date: string;
  type: 'entry' | 'exit';
  price: number;
  pnl?: number;
  pnlPercent?: number;
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

function generateMockBacktest(config: BacktestConfig): BacktestResult {
  const days = Math.floor(
    (new Date(config.endDate).getTime() - new Date(config.startDate).getTime()) / (1000 * 60 * 60 * 24)
  );

  const equityCurve: BacktestResult['equityCurve'] = [];
  const trades: Trade[] = [];
  const monthlyReturns: BacktestResult['monthlyReturns'] = [];

  let capital = config.initialCapital;
  let benchmark = config.initialCapital;
  let peak = capital;
  let maxDrawdown = 0;
  let wins = 0;
  let totalWinAmount = 0;
  let totalLossAmount = 0;

  const winRateBase = config.strategy === 'bull_spread' ? 0.58 : config.strategy === 'covered_call' ? 0.65 : 0.45;
  const returnBase = config.strategy === 'bull_spread' ? 0.012 : config.strategy === 'covered_call' ? 0.008 : 0.025;

  for (let i = 0; i <= days; i++) {
    const date = new Date(config.startDate);
    date.setDate(date.getDate() + i);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    // Simulate daily price movement
    const dailyReturn = (Math.random() - 0.48) * 0.02;
    benchmark *= 1 + dailyReturn;

    // Simulate strategy trades (every 15-30 days)
    if (i > 0 && i % Math.floor(15 + Math.random() * 15) === 0) {
      const isWin = Math.random() < winRateBase;
      const tradeReturn = isWin
        ? returnBase * (0.5 + Math.random())
        : -returnBase * (0.3 + Math.random() * 0.7);

      capital *= 1 + tradeReturn;
      if (capital > peak) peak = capital;
      const drawdown = (peak - capital) / peak;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;

      if (isWin) {
        wins++;
        totalWinAmount += tradeReturn * capital;
      } else {
        totalLossAmount += Math.abs(tradeReturn * capital);
      }

      trades.push({
        date: dateStr,
        type: 'exit',
        price: 100 + Math.random() * 50,
        pnl: tradeReturn * capital,
        pnlPercent: tradeReturn * 100,
      });
    }

    equityCurve.push({
      date: dateStr,
      value: capital,
      benchmark: benchmark,
    });
  }

  const totalTrades = trades.length;
  const winRate = totalTrades > 0 ? wins / totalTrades : 0;
  const profitFactor = totalLossAmount > 0 ? totalWinAmount / totalLossAmount : totalWinAmount > 0 ? 999 : 0;
  const totalReturn = (capital - config.initialCapital) / config.initialCapital;
  const years = days / 365;
  const annualizedReturn = years > 0 ? Math.pow(1 + totalReturn, 1 / years) - 1 : totalReturn;

  // Generate monthly returns
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  for (let i = 0; i < 12; i++) {
    monthlyReturns.push({
      month: months[i],
      return: (Math.random() - 0.35) * 15,
    });
  }

  // Calculate Sharpe ratio (simplified)
  const dailyReturns = equityCurve.slice(1).map((d, i) => (d.value - equityCurve[i].value) / equityCurve[i].value);
  const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length;
  const stdDev = Math.sqrt(dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / dailyReturns.length);
  const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;

  return {
    equityCurve,
    trades,
    metrics: {
      totalReturn: totalReturn * 100,
      annualizedReturn: annualizedReturn * 100,
      winRate: winRate * 100,
      profitFactor,
      maxDrawdown: maxDrawdown * 100,
      sharpeRatio,
      totalTrades,
      avgWin: winRate > 0 ? (totalWinAmount / wins) : 0,
      avgLoss: totalTrades > wins ? (totalLossAmount / (totalTrades - wins)) : 0,
      bestTrade: trades.length > 0 ? Math.max(...trades.map((t) => t.pnlPercent || 0)) : 0,
      worstTrade: trades.length > 0 ? Math.min(...trades.map((t) => t.pnlPercent || 0)) : 0,
    },
    monthlyReturns,
  };
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

export default function BacktestPage() {
  const [config, setConfig] = useState<BacktestConfig>({
    symbol: 'QQQ',
    strategy: 'bull_spread',
    startDate: '2024-01-01',
    endDate: '2024-12-31',
    initialCapital: 100000,
  });

  const [result, setResult] = useState<BacktestResult | null>(null);

  const runBacktest = () => {
    setResult(generateMockBacktest(config));
  };

  const strategyNames: Record<string, string> = {
    leaps_call: 'LEAPS Call',
    bull_spread: 'Bull Spread',
    covered_call: 'Covered Call',
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-6xl space-y-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-100">Strategy Backtest</h1>
              <p className="mt-1 text-sm text-slate-500">Simulate historical performance of options strategies</p>
            </div>

            {/* Config Panel */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="mb-3 text-sm font-semibold text-slate-300">Configuration</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div>
                  <label className="mb-1 block text-xs text-slate-500">Symbol</label>
                  <select
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
                    value={config.symbol}
                    onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                  >
                    {['QQQ', 'SPY', 'NVDA', 'AAPL', 'TSLA', 'MSFT', 'PLTR'].map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
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
                  <label className="mb-1 block text-xs text-slate-500">Start Date</label>
                  <input
                    type="date"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
                    value={config.startDate}
                    onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-500">End Date</label>
                  <input
                    type="date"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
                    value={config.endDate}
                    onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={runBacktest}
                    className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
                  >
                    Run Backtest
                  </button>
                </div>
              </div>
            </div>

            {result && (
              <>
                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                  <MetricCard
                    label="Total Return"
                    value={result.metrics.totalReturn}
                    suffix="%"
                    color={result.metrics.totalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}
                  />
                  <MetricCard label="Annualized" value={result.metrics.annualizedReturn} suffix="%" />
                  <MetricCard label="Win Rate" value={result.metrics.winRate} suffix="%" />
                  <MetricCard label="Profit Factor" value={result.metrics.profitFactor} />
                  <MetricCard
                    label="Max Drawdown"
                    value={result.metrics.maxDrawdown}
                    suffix="%"
                    color="text-rose-400"
                  />
                  <MetricCard label="Sharpe Ratio" value={result.metrics.sharpeRatio} />
                </div>

                {/* Equity Curve */}
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <h3 className="mb-4 text-sm font-semibold text-slate-300">
                    Equity Curve — {config.symbol} {strategyNames[config.strategy]}
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
                      <XAxis
                        dataKey="date"
                        stroke="#475569"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        interval={Math.floor(result.equityCurve.length / 8)}
                      />
                      <YAxis
                        stroke="#475569"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`}
                        width={50}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          border: '1px solid #1e293b',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(value: unknown) => {
                          const num = typeof value === 'number' ? value : Number(value);
                          return [`$${num.toFixed(0)}`, ''];
                        }}
                        labelStyle={{ color: '#94a3b8' }}
                      />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#6366f1"
                        strokeWidth={2}
                        fill="url(#equityGradient)"
                        dot={false}
                        name="Strategy"
                      />
                      <Line
                        type="monotone"
                        dataKey="benchmark"
                        stroke="#475569"
                        strokeWidth={1}
                        strokeDasharray="4 4"
                        dot={false}
                        name="Buy & Hold"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Monthly Returns + Trade Stats */}
                <div className="grid gap-4 lg:grid-cols-2">
                  {/* Monthly Returns */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <h3 className="mb-4 text-sm font-semibold text-slate-300">Monthly Returns</h3>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={result.monthlyReturns} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="month" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis
                          stroke="#475569"
                          fontSize={11}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                          width={40}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            border: '1px solid #1e293b',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                          formatter={(value: unknown) => {
                            const num = typeof value === 'number' ? value : Number(value);
                            return [`${num.toFixed(2)}%`, 'Return'];
                          }}
                        />
                        <Bar dataKey="return" radius={[4, 4, 0, 0]}>
                          {result.monthlyReturns.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={entry.return >= 0 ? '#10b981' : '#f43f5e'}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Trade Distribution */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <h3 className="mb-4 text-sm font-semibold text-slate-300">Trade Statistics</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Total Trades</span>
                        <span className="text-sm font-medium text-slate-200">{result.metrics.totalTrades}</span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Winning Trades</span>
                        <span className="text-sm font-medium text-emerald-400">
                          {Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100))}
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Losing Trades</span>
                        <span className="text-sm font-medium text-rose-400">
                          {result.metrics.totalTrades -
                            Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100))}
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Average Win</span>
                        <span className="text-sm font-medium text-emerald-400">
                          ${result.metrics.avgWin.toFixed(0)}
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Average Loss</span>
                        <span className="text-sm font-medium text-rose-400">
                          ${result.metrics.avgLoss.toFixed(0)}
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs text-slate-500">Best Trade</span>
                        <span className="text-sm font-medium text-emerald-400">
                          +{result.metrics.bestTrade.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-slate-500">Worst Trade</span>
                        <span className="text-sm font-medium text-rose-400">
                          {result.metrics.worstTrade.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trade List */}
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
                              <td className={`py-2 ${(trade.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {(trade.pnl || 0) >= 0 ? '+' : ''}${(trade.pnl || 0).toFixed(0)}
                              </td>
                              <td className={`py-2 ${(trade.pnlPercent || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {(trade.pnlPercent || 0) >= 0 ? '+' : ''}
                                {(trade.pnlPercent || 0).toFixed(2)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {result.trades.length > 10 && (
                        <p className="mt-2 text-xs text-slate-500">
                          Showing 10 of {result.trades.length} trades
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
