'use client';

import {
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { TrackedDecision } from '@/lib/api';
import { useLocale } from '@/components/LocaleProvider';
import { getMessage } from '@/i18n/get-message';
import type { MessageKey } from '@/i18n/types';

interface TrackingDecisionTableProps {
  decisions: TrackedDecision[] | null;
}

const STATUS_CONFIG: Record<string, { color: 'success' | 'error' | 'default' | 'primary' | 'warning'; key: MessageKey }> = {
  hit_target: { color: 'success', key: 'interaction.trackingStatusHit' },
  hit_stop: { color: 'error', key: 'interaction.trackingStatusStop' },
  expired: { color: 'default', key: 'interaction.trackingStatusExpired' },
  active: { color: 'primary', key: 'interaction.trackingStatusActive' },
  pending: { color: 'warning', key: 'interaction.trackingStatusPending' },
};

export default function TrackingDecisionTable({ decisions }: TrackingDecisionTableProps) {
  const { locale } = useLocale();

  return (
    <Paper elevation={0} sx={{ borderRadius: '16px', border: '1px solid', borderColor: 'divider', overflow: 'hidden' }}>
      <Typography variant="subtitle1" fontWeight={700} sx={{ px: 2.5, pt: 2, pb: 1 }}>
        {getMessage(locale, 'interaction.trackingDecisions')}
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>Symbol</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>
                {getMessage(locale, 'interaction.backtestStrategy')}
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
              <TableCell sx={{ fontWeight: 700 }} align="right">Entry</TableCell>
              <TableCell sx={{ fontWeight: 700 }} align="right">Target</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 700 }} align="right">PnL%</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!decisions || decisions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ color: 'text.secondary', py: 4 }}>
                  {getMessage(locale, 'interaction.trackingEmpty')}
                </TableCell>
              </TableRow>
            ) : (
              decisions.map((d) => {
                const statusConfig = STATUS_CONFIG[d.status] || {
                  color: 'default' as const,
                  key: 'interaction.trackingStatusPending',
                };
                return (
                  <TableRow key={d.id}>
                    <TableCell sx={{ fontWeight: 600 }}>{d.symbol}</TableCell>
                    <TableCell>{d.strategyType}</TableCell>
                    <TableCell>{d.recommendedAt?.split('T')[0] ?? '—'}</TableCell>
                    <TableCell align="right">{d.entryPrice.toFixed(2)}</TableCell>
                    <TableCell align="right">{d.targetPrice != null ? d.targetPrice.toFixed(2) : '—'}</TableCell>
                    <TableCell>
                      <Chip
                        label={getMessage(locale, statusConfig.key)}
                        size="small"
                        color={statusConfig.color}
                      />
                    </TableCell>
                    <TableCell align="right">
                      {d.pnlPct != null ? (
                        <span style={{ color: d.pnlPct >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {d.pnlPct > 0 ? '+' : ''}{d.pnlPct.toFixed(2)}%
                        </span>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}