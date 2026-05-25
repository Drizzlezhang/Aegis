'use client';

import { Chip, Paper, Stack, Typography } from '@mui/material';
import type { TrackingStats } from '@/lib/api';
import { useLocale } from '@/components/LocaleProvider';
import { getMessage } from '@/i18n/get-message';

interface TrackingSummaryCardsProps {
  stats: TrackingStats | null;
}

export default function TrackingSummaryCards({ stats }: TrackingSummaryCardsProps) {
  const { locale } = useLocale();

  const cards = [
    {
      label: getMessage(locale, 'interaction.trackingHitRate'),
      value: stats ? `${(stats.hitRate * 100).toFixed(1)}%` : '—',
    },
    {
      label: getMessage(locale, 'interaction.trackingAvgPnl'),
      value: stats ? `${stats.avgPnlPct > 0 ? '+' : ''}${stats.avgPnlPct.toFixed(2)}%` : '—',
    },
    {
      label: getMessage(locale, 'interaction.trackingTotal'),
      value: stats ? String(stats.total) : '—',
    },
    {
      label: getMessage(locale, 'interaction.trackingPending'),
      value: stats ? String(stats.pending) : '—',
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Paper
          key={card.label}
          elevation={0}
          sx={{ p: 2.5, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}
        >
          <Stack spacing={0.5}>
            <Typography variant="caption" color="text.secondary">
              {card.label}
            </Typography>
            <Typography variant="h5" fontWeight={700}>
              {card.value}
            </Typography>
          </Stack>
        </Paper>
      ))}
    </div>
  );
}