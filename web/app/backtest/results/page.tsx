'use client';

import { useEffect, useState } from 'react';
import { Typography } from '@mui/material';
import { BacktestResults } from '@/components/BacktestResults';
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

export default function BacktestResultsPage() {
  const [stats, setStats] = useState<ResultsProps | null>(null);
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

  if (loading) {
    return <LoadingSkeleton variant="table" rows={8} />;
  }

  if (!stats) {
    return <Typography sx={{ p: 3 }}>No data</Typography>;
  }

  return <BacktestResults {...stats} />;
}
