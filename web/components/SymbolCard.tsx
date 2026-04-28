'use client';

import Link from 'next/link';
import { LinearProgress, Paper, Stack, Typography } from '@mui/material';
import type { SymbolInfo } from '@/lib/api';
import { getMessage } from '@/i18n/get-message';
import { getChangeColorClasses } from '@/lib/change-color';
import { useLocale } from './LocaleProvider';

interface SymbolCardProps {
  symbol: SymbolInfo;
}

function formatVolume(n: number): string {
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(2) + 'B';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return n.toString();
}

export default function SymbolCard({ symbol }: SymbolCardProps) {
  const positive = symbol.change >= 0;
  const changeColors = getChangeColorClasses(positive);
  const { locale } = useLocale();

  return (
    <Paper
      component={Link}
      href={`/symbol/${symbol.symbol}`}
      elevation={0}
      sx={{
        p: 2.25,
        borderRadius: '28px',
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        textDecoration: 'none',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '0 16px 32px rgba(103, 80, 164, 0.14)',
          borderColor: 'primary.main',
        },
      }}
    >
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={2}>
        <div>
          <Typography variant="h6" sx={{ fontWeight: 800, color: 'text.primary' }}>
            {symbol.symbol}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {symbol.name}
          </Typography>
        </div>
        <StatusBadge status={symbol.analysisStatus} locale={locale} />
      </Stack>

      <Stack direction="row" alignItems="flex-end" justifyContent="space-between" sx={{ mt: 2.5 }}>
        <div>
          <Typography variant="h5" sx={{ fontWeight: 800, color: 'text.primary' }}>
            ${symbol.price.toFixed(2)}
          </Typography>
          <p className={`text-sm font-semibold ${changeColors.text}`}>
            {positive ? '+' : ''}
            {symbol.change.toFixed(2)} ({positive ? '+' : ''}
            {symbol.changePercent.toFixed(2)}%)
          </p>
        </div>
        <div className="text-right">
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.vol')}
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {formatVolume(symbol.volume)}
          </Typography>
        </div>
      </Stack>

      <div className="mt-4">
        <TrendIndicator trend={symbol.trend} locale={locale} />
      </div>
    </Paper>
  );
}

function StatusBadge({ status, locale }: { status: SymbolInfo['analysisStatus']; locale: 'zh-CN' | 'en' }) {
  if (status === 'completed') return <span className="badge-green">{getMessage(locale, 'interaction.done')}</span>;
  if (status === 'pending') return <span className="badge-amber">{getMessage(locale, 'interaction.pending')}</span>;
  return <span className="badge-red">{getMessage(locale, 'common.error')}</span>;
}

function TrendIndicator({ trend, locale }: { trend: SymbolInfo['trend']; locale: 'zh-CN' | 'en' }) {
  const value = trend === 'down' ? 20 : trend === 'neutral' ? 50 : 85;
  const barColor = trend === 'down' ? '#10b981' : trend === 'neutral' ? '#f59e0b' : '#f43f5e';
  const label =
    trend === 'down'
      ? getMessage(locale, 'interaction.bearish')
      : trend === 'neutral'
        ? getMessage(locale, 'interaction.neutral')
        : getMessage(locale, 'interaction.bullish');

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          {label}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          {value}%
        </Typography>
      </div>
      <LinearProgress
        variant="determinate"
        value={value}
        aria-label={label}
        sx={{
          height: 8,
          borderRadius: 999,
          bgcolor: 'action.hover',
          '& .MuiLinearProgress-bar': {
            borderRadius: 999,
            backgroundColor: barColor,
          },
        }}
      />
    </div>
  );
}
