'use client';

import React from 'react';
import { Box, Card, CardContent, Typography, Grid, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getMessage } from '@/i18n/get-message';
import type { Locale } from '@/i18n/types';

interface BacktestStats {
  total_trades: number;
  win_rate: number;
  avg_pnl_pct: number;
  max_drawdown_pct: number | null;
  profit_factor: number | null;
  avg_days_held: number;
}

interface EquityPoint {
  date: string;
  value: number;
}

interface MonthlyReturn {
  month: string;
  pnl_pct: number;
}

interface StrategyBreakdown {
  strategy_type: string;
  count: number;
  win_rate: number;
  avg_pnl: number;
  max_drawdown: number | null;
}

interface BacktestResultsProps {
  stats: BacktestStats;
  equityCurve: EquityPoint[];
  monthlyReturns: MonthlyReturn[];
  strategyBreakdown: StrategyBreakdown[];
  locale?: Locale;
}

export function BacktestResults({ stats, equityCurve, monthlyReturns, strategyBreakdown, locale = 'zh-CN' }: BacktestResultsProps) {
  const formatPct = (value: number | null, options: { signed?: boolean; negativePrefix?: boolean } = {}) => {
    if (value === null) {
      return '--';
    }
    const prefix = options.negativePrefix ? '-' : options.signed && value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(1)}%`;
  };

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">{getMessage(locale, 'interaction.backtestWinRate')}</Typography>
              <Typography variant="h5" fontWeight="bold">{(stats.win_rate * 100).toFixed(1)}%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">{getMessage(locale, 'interaction.backtestAvgPnl')}</Typography>
              <Typography variant="h5" fontWeight="bold" color={stats.avg_pnl_pct >= 0 ? 'error.main' : 'success.main'}>
                {stats.avg_pnl_pct >= 0 ? '+' : ''}{stats.avg_pnl_pct.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">{getMessage(locale, 'interaction.backtestMaxDrawdown')}</Typography>
              <Typography variant="h5" fontWeight="bold" color="success.main">{formatPct(stats.max_drawdown_pct, { negativePrefix: true })}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="caption" color="text.secondary">{getMessage(locale, 'interaction.backtestTrades')}</Typography>
              <Typography variant="h5" fontWeight="bold">{stats.total_trades}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>{getMessage(locale, 'interaction.backtestEquityCurve')}</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={equityCurve}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#1976d2" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>{getMessage(locale, 'interaction.backtestMonthly')}</Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={monthlyReturns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="pnl_pct" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Strategy Breakdown */}
      {strategyBreakdown.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>Strategy Breakdown</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Strategy</TableCell>
                  <TableCell align="right">Count</TableCell>
                  <TableCell align="right">{getMessage(locale, 'interaction.backtestWinRate')}</TableCell>
                  <TableCell align="right">{getMessage(locale, 'interaction.backtestAvgPnl')}</TableCell>
                  <TableCell align="right">{getMessage(locale, 'interaction.backtestMaxDrawdown')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {strategyBreakdown.map(row => (
                  <TableRow key={row.strategy_type}>
                    <TableCell>{row.strategy_type}</TableCell>
                    <TableCell align="right">{row.count}</TableCell>
                    <TableCell align="right">{(row.win_rate * 100).toFixed(1)}%</TableCell>
                    <TableCell align="right" sx={{ color: row.avg_pnl >= 0 ? 'error.main' : 'success.main' }}>
                      {row.avg_pnl >= 0 ? '+' : ''}{row.avg_pnl.toFixed(1)}%
                    </TableCell>
                    <TableCell align="right">{formatPct(row.max_drawdown, { negativePrefix: true })}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
