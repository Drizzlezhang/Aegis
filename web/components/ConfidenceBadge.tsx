'use client';

import { LinearProgress, Stack, Typography } from '@mui/material';
import { useLocale } from './LocaleProvider';
import { getMessage } from '@/i18n/get-message';

interface ConfidenceBadgeProps {
  value: number | null | undefined;
}

export default function ConfidenceBadge({ value }: ConfidenceBadgeProps) {
  const { locale } = useLocale();

  if (value == null || isNaN(value)) return null;

  const percentage = Math.round(value * 100);
  const color = value >= 0.8 ? 'success' : value >= 0.6 ? 'warning' : 'error';
  const label =
    value >= 0.8
      ? getMessage(locale, 'interaction.confidenceHigh')
      : value >= 0.6
        ? getMessage(locale, 'interaction.confidenceMedium')
        : getMessage(locale, 'interaction.confidenceLow');

  return (
    <Stack spacing={0.5} sx={{ width: '100%', minWidth: 120 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <LinearProgress
          variant="determinate"
          value={percentage}
          color={color}
          sx={{ flex: 1, height: 8, borderRadius: 4 }}
        />
        <Typography variant="body2" fontWeight={700} sx={{ minWidth: 36, textAlign: 'right' }}>
          {percentage}%
        </Typography>
      </Stack>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Stack>
  );
}