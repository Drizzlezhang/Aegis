'use client';

import { useEffect, useMemo, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { BacktestResults } from '@/components/BacktestResults';
import EquityCurveChart from '@/components/EquityCurveChart';
import type { EquityCurvePoint } from '@/components/EquityCurveChart';
import DrawdownChart from '@/components/DrawdownChart';
import type { DrawdownPoint } from '@/components/DrawdownChart';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { getStrategyPerformance, getTradingStats } from '@/lib/api';
import type { StrategyPerformanceData, TradingStatsData } from '@/lib/api';

type ResultsProps = React.ComponentProps<typeof BacktestResults>;

function adaptStats(statsData: TradingStatsData, perfData: StrategyPerformanceData[]): ResultsProps {
  return {
    stats: {
      total_trades: statsData.total_positions,
      win_rate: statsData.win_rate,
      avg_pnl_pct: statsData.avg_pnl_pct,
      max_drawdown_pct: null,
      profit_factor: null,
      avg_days_held: statsData.avg_holding_days,
    },
    equityCurve: Object.entries(statsData.monthly_pnl || {}).map(([month, pnl]) => ({
      date: month,
      value: pnl,
    })),
    monthlyReturns: Object.entries(statsData.monthly_pnl || {}).map(([month, pnl]) => ({
      month,
      pnl_pct: pnl,
    })),
    strategyBreakdown: perfData.map((p) => ({
      strategy_type: p.strategy_type,
      count: p.count,
      win_rate: p.win_rate,
      avg_pnl: p.avg_pnl,
      max_drawdown: null,
    })),
  };
}

function computeChartData(monthlyPnl: Record<string, number>): {
  equityCurve: EquityCurvePoint[];
  drawdown: DrawdownPoint[];
  maxDrawdown: number;
} {
  const entries = Object.entries(monthlyPnl || {}).sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) {
    return { equityCurve: [], drawdown: [], maxDrawdown: 0 };
  }

  const equityCurve: EquityCurvePoint[] = [];
  const drawdown: DrawdownPoint[] = [];
  let cumulative = 0;
  let peak = 0;
  let maxDrawdown = 0;

  for (const [month, pnl] of entries) {
    cumulative += pnl;
    if (cumulative > peak) {
      peak = cumulative;
    }
    const dd = peak > 0 ? (cumulative - peak) / peak : 0;
    if (dd < maxDrawdown) {
      maxDrawdown = dd;
    }
    equityCurve.push({ date: month, equity: cumulative });
    drawdown.push({ date: month, drawdown: dd });
  }

  return { equityCurve, drawdown, maxDrawdown };
}

export default function BacktestResultsPage() {
  const [stats, setStats] = useState<ResultsProps | null>(null);
  const [monthlyPnl, setMonthlyPnl] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function fetchData() {
      try {
        const [statsData, perfData] = await Promise.all([
          getTradingStats(),
          getStrategyPerformance(),
        ]);
        if (active) {
          setStats(adaptStats(statsData, perfData));
          setMonthlyPnl(statsData.monthly_pnl || {});
        }
      } catch (error) {
        console.error('Failed to load stats', error);
        if (active) {
          setStats(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      active = false;
    };
  }, []);

  const { equityCurve, drawdown, maxDrawdown } = useMemo(
    () => computeChartData(monthlyPnl),
    [monthlyPnl],
  );

  if (loading) {
    return <LoadingSkeleton variant="table" rows={8} />;
  }

  if (!stats) {
    return <Typography sx={{ p: 3 }}>No data</Typography>;
  }

  return (
    <Box>
      <BacktestResults {...stats} />
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Equity Curve
        </Typography>
        <EquityCurveChart data={equityCurve} />
      </Box>
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Drawdown
        </Typography>
        <DrawdownChart data={drawdown} maxDrawdown={maxDrawdown} />
      </Box>
    </Box>
  );
}
