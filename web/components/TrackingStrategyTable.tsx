'use client';

import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { TrackingStats } from '@/lib/api';
import { useLocale } from '@/components/LocaleProvider';
import { getMessage } from '@/i18n/get-message';

interface TrackingStrategyTableProps {
  stats: TrackingStats | null;
}

export default function TrackingStrategyTable({ stats }: TrackingStrategyTableProps) {
  const { locale } = useLocale();

  const strategies = stats?.byStrategy
    ? Object.entries(stats.byStrategy).map(([name, data]) => ({
        name,
        total: data.total,
        hitRate: data.hitRate,
      }))
    : [];

  return (
    <Paper elevation={0} sx={{ borderRadius: '16px', border: '1px solid', borderColor: 'divider', overflow: 'hidden' }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ px: 2.5, pt: 2, pb: 1 }}>
        {getMessage(locale, 'interaction.trackingByStrategy')}
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>
                {getMessage(locale, 'interaction.backtestStrategy')}
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }} align="right">
                {getMessage(locale, 'interaction.backtestTrades')}
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }} align="right">
                {getMessage(locale, 'interaction.trackingHitRate')}
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {strategies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  —
                </TableCell>
              </TableRow>
            ) : (
              strategies.map((s) => (
                <TableRow key={s.name}>
                  <TableCell sx={{ fontWeight: 600 }}>{s.name}</TableCell>
                  <TableCell align="right">{s.total}</TableCell>
                  <TableCell align="right">{(s.hitRate * 100).toFixed(1)}%</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}