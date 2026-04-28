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
import { Button, Chip, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { runBacktest } from '@/lib/api';
import { getMessage } from '@/i18n/get-message';
import { getChangeColorClasses } from '@/lib/change-color';
import { useLocale } from './LocaleProvider';

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

function MetricCard({ label, value, suffix = '', color = 'text-[var(--foreground)]' }: { label: string; value: string | number; suffix?: string; color?: string }) {
  return (
    <Paper elevation={0} className="card-muted">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${color}`}>
        {typeof value === 'number' ? value.toFixed(2) : value}
        {suffix}
      </p>
    </Paper>
  );
}

function getChangeTextClass(value: number) {
  return getChangeColorClasses(value >= 0).text;
}

function getChangeSolidColor(value: number) {
  return getChangeColorClasses(value >= 0).solid;
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
  const { locale } = useLocale();

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
      setError(err instanceof Error ? err.message : getMessage(locale, 'interaction.backtestFailed'));
    } finally {
      setLoading(false);
    }
  };

  const strategyNames: Record<string, string> = {
    leaps_call: getMessage(locale, 'interaction.leapsCall'),
    bull_spread: 'Bull Spread',
    covered_call: 'Covered Call',
  };

  const signalTypeNames: Record<string, string> = {
    sma_crossover: 'SMA Crossover',
    rsi: getMessage(locale, 'interaction.rsi'),
    sma_rsi_combo: getMessage(locale, 'interaction.smaRsiCombo'),
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="card">
        <h1 className="text-3xl font-bold text-[var(--foreground)]">策略回测</h1>
        <p className="mt-2 text-sm text-slate-500">模拟期权策略的历史表现</p>
      </div>

      <Paper elevation={0} className="card">
        <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.configuration')}
        </Typography>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <TextField
            select
            label="Symbol"
            value={config.symbol}
            onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
            size="small"
          >
            {['QQQ', 'SPY', 'NVDA', 'AAPL', 'TSLA', 'MSFT', 'PLTR'].map((s) => (
              <MenuItem key={s} value={s}>{s}</MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label={getMessage(locale, 'interaction.strategy')}
            value={config.strategy}
            onChange={(e) => setConfig({ ...config, strategy: e.target.value as BacktestConfig['strategy'] })}
            size="small"
          >
            <MenuItem value="leaps_call">{getMessage(locale, 'interaction.leapsCall')}</MenuItem>
            <MenuItem value="bull_spread">Bull Spread</MenuItem>
            <MenuItem value="covered_call">Covered Call</MenuItem>
          </TextField>

          <TextField
            select
            label={getMessage(locale, 'interaction.signalType')}
            value={config.signalType}
            onChange={(e) => setConfig({ ...config, signalType: e.target.value as BacktestConfig['signalType'] })}
            size="small"
          >
            <MenuItem value="sma_crossover">SMA Crossover</MenuItem>
            <MenuItem value="rsi">{getMessage(locale, 'interaction.rsi')}</MenuItem>
            <MenuItem value="sma_rsi_combo">{getMessage(locale, 'interaction.smaRsiCombo')}</MenuItem>
          </TextField>

          <TextField
            type="date"
            label={getMessage(locale, 'interaction.startDate')}
            value={config.startDate}
            onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
            size="small"
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <TextField
            type="date"
            label={getMessage(locale, 'interaction.endDate')}
            value={config.endDate}
            onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
            size="small"
            slotProps={{ inputLabel: { shrink: true } }}
          />

          <div className="flex items-end">
            <Button onClick={handleRunBacktest} disabled={loading} variant="contained" fullWidth sx={{ borderRadius: '16px', py: 1.2, fontWeight: 700 }}>
              {loading ? getMessage(locale, 'interaction.running') : getMessage(locale, 'interaction.runBacktest')}
            </Button>
          </div>
        </div>
      </Paper>

      {error && <div className="card-muted border-rose-300/40 bg-rose-500/10 text-sm text-rose-400">{error}</div>}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <MetricCard label={getMessage(locale, 'interaction.totalReturn')} value={result.metrics.totalReturn} suffix="%" color={getChangeTextClass(result.metrics.totalReturn)} />
            <MetricCard label={getMessage(locale, 'interaction.annualized')} value={result.metrics.annualizedReturn} suffix="%" />
            <MetricCard label={getMessage(locale, 'interaction.winRate')} value={result.metrics.winRate} suffix="%" />
            <MetricCard label={getMessage(locale, 'interaction.profitFactor')} value={result.metrics.profitFactor} />
            <MetricCard label={getMessage(locale, 'interaction.maxDrawdown')} value={result.metrics.maxDrawdown} suffix="%" color="text-rose-400" />
            <MetricCard label={getMessage(locale, 'interaction.sharpeRatio')} value={result.metrics.sharpeRatio} />
          </div>

          <Paper elevation={0} className="card">
            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
              {getMessage(locale, 'interaction.equityCurve')} — {config.symbol} {strategyNames[config.strategy]} ({signalTypeNames[config.signalType]})
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={result.equityCurve} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6750A4" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="#6750A4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,140,0.2)" />
                <XAxis dataKey="date" stroke="#7c7c8c" fontSize={10} tickLine={false} axisLine={false} interval={Math.floor(result.equityCurve.length / 8)} />
                <YAxis stroke="#7c7c8c" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`} width={50} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'rgba(24,24,30,0.96)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', fontSize: '12px' }}
                  formatter={(value: unknown) => {
                    const num = typeof value === 'number' ? value : Number(value);
                    return [`$${num.toFixed(0)}`, ''];
                  }}
                  labelStyle={{ color: '#b0b0bb' }}
                />
                <Area type="monotone" dataKey="value" stroke="#6750A4" strokeWidth={2} fill="url(#equityGradient)" dot={false} name="Strategy" />
                <Line type="monotone" dataKey="benchmark" stroke="#8f8f9d" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Buy & Hold" />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>

          <div className="grid gap-4 lg:grid-cols-2">
            <Paper elevation={0} className="card">
              <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
                {getMessage(locale, 'interaction.monthlyReturns')}
              </Typography>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={result.monthlyReturns} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,140,0.2)" vertical={false} />
                  <XAxis dataKey="month" stroke="#7c7c8c" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#7c7c8c" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} width={40} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(24,24,30,0.96)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', fontSize: '12px' }}
                    formatter={(value: unknown) => {
                      const num = typeof value === 'number' ? value : Number(value);
                      return [`${num.toFixed(2)}%`, getMessage(locale, 'interaction.return')];
                    }}
                  />
                  <Bar dataKey="return" radius={[8, 8, 0, 0]}>
                    {result.monthlyReturns.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getChangeSolidColor(entry.return)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Paper>

            <Paper elevation={0} className="card">
              <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
                {getMessage(locale, 'interaction.tradeStatistics')}
              </Typography>
              <div className="space-y-3">
                <StatRow label={getMessage(locale, 'interaction.totalTrades')} value={String(result.metrics.totalTrades)} />
                <StatRow label={getMessage(locale, 'interaction.winningTrades')} value={String(Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100)))} valueClass={getChangeTextClass(result.metrics.avgWin)} />
                <StatRow label={getMessage(locale, 'interaction.losingTrades')} value={String(result.metrics.totalTrades - Math.round(result.metrics.totalTrades * (result.metrics.winRate / 100)))} valueClass={getChangeTextClass(result.metrics.avgLoss * -1)} />
                <StatRow label={getMessage(locale, 'interaction.averageWin')} value={`$${result.metrics.avgWin.toFixed(0)}`} valueClass={getChangeTextClass(result.metrics.avgWin)} />
                <StatRow label={getMessage(locale, 'interaction.averageLoss')} value={`$${result.metrics.avgLoss.toFixed(0)}`} valueClass={getChangeTextClass(result.metrics.avgLoss * -1)} />
                <StatRow label={getMessage(locale, 'interaction.bestTrade')} value={`+${result.metrics.bestTrade.toFixed(2)}%`} valueClass={getChangeTextClass(result.metrics.bestTrade)} />
                <StatRow label={getMessage(locale, 'interaction.worstTrade')} value={`${result.metrics.worstTrade.toFixed(2)}%`} valueClass={getChangeTextClass(result.metrics.worstTrade)} />
              </div>
            </Paper>
          </div>

          {result.trades.length > 0 && (
            <Paper elevation={0} className="card">
              <div className="mb-3 flex items-center justify-between">
                <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
                  {getMessage(locale, 'interaction.tradeHistory')}
                </Typography>
                <Chip label={`${result.trades.length} trades`} size="small" variant="outlined" />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left" style={{ borderColor: 'var(--outline)' }}>
                      <th className="pb-2 text-xs font-medium text-slate-500">{getMessage(locale, 'interaction.date')}</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">{getMessage(locale, 'interaction.price')}</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">P&L</th>
                      <th className="pb-2 text-xs font-medium text-slate-500">{getMessage(locale, 'interaction.return')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(0, 10).map((trade, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                        <td className="py-2 text-[var(--foreground)]">{trade.date}</td>
                        <td className="py-2 text-[var(--foreground)]">${trade.price.toFixed(2)}</td>
                        <td className={`py-2 ${getChangeTextClass(trade.pnl || 0)}`}>{(trade.pnl || 0) >= 0 ? '+' : ''}${(trade.pnl || 0).toFixed(0)}</td>
                        <td className={`py-2 ${getChangeTextClass(trade.pnlPercent || 0)}`}>{(trade.pnlPercent || 0) >= 0 ? '+' : ''}{(trade.pnlPercent || 0).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {result.trades.length > 10 && <p className="mt-2 text-xs text-slate-500">{getMessage(locale, 'interaction.showingTrades').replace('{shown}', '10').replace('{total}', String(result.trades.length))}</p>}
              </div>
            </Paper>
          )}
        </>
      )}
    </div>
  );
}

function StatRow({ label, value, valueClass = 'text-[var(--foreground)]' }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex justify-between border-b pb-2" style={{ borderColor: 'var(--outline)' }}>
      <span className="text-xs text-slate-500">{label}</span>
      <span className={`text-sm font-medium ${valueClass}`}>{value}</span>
    </div>
  );
}
