'use client';

import { Paper, Stack, Typography } from '@mui/material';
import { getChangeColorClasses } from '@/lib/change-color';

export interface MarketIndexProps {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

export default function MarketIndexCard({
  symbol,
  name,
  price,
  change,
  change_percent,
}: MarketIndexProps) {
  const isUp = change >= 0;
  const changeColors = getChangeColorClasses(isUp);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.25,
        borderRadius: '24px',
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
        <div>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
            {name}
          </Typography>
          <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 800, color: 'text.primary' }}>
            {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </Typography>
        </div>
        <div className={`flex items-center gap-1 rounded-full px-2.5 py-1 ${changeColors.bg}`}>
          <span className={`text-xs ${changeColors.text}`}>{isUp ? '▲' : '▼'}</span>
          <span className={`text-xs font-semibold ${changeColors.text}`}>
            {isUp ? '+' : ''}
            {change_percent.toFixed(2)}%
          </span>
        </div>
      </Stack>
      <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'text.secondary' }}>
        {symbol}
      </Typography>
    </Paper>
  );
}
