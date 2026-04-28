'use client';

import { Chip, Paper, Typography } from '@mui/material';
import { MarketIndexData } from '@/lib/api';
import { getChangeColorClasses } from '@/lib/change-color';
import { getSentimentStyle, getVixStyle, parseMarketContext } from '@/lib/market-context';

interface MarketSentimentBannerProps {
  indices: MarketIndexData[];
}

function changeBadge(label: string, value: number | null) {
  if (value === null) return null;
  const isUp = value >= 0;
  const changeColors = getChangeColorClasses(isUp);
  return (
    <span className={`text-xs ${changeColors.text}`}>
      {label}: {isUp ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}

export default function MarketSentimentBanner({ indices }: MarketSentimentBannerProps) {
  if (!indices || indices.length === 0) return null;

  const ctx = parseMarketContext(indices);
  const sentimentStyle = getSentimentStyle(ctx.sentiment);

  return (
    <Paper elevation={0} className="card-muted">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Market Sentiment
          </Typography>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${sentimentStyle.bg} ${sentimentStyle.text}`}>
            {sentimentStyle.label}
          </span>
        </div>

        <div>
          {ctx.vix !== null ? (
            <span className={`text-xs font-medium ${getVixStyle(ctx.regime)}`}>
              VIX: {ctx.vix.toFixed(2)}
            </span>
          ) : (
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>VIX: —</Typography>
          )}
        </div>

        <div className="flex items-center gap-3">
          {changeBadge('SPX', ctx.spxChange)}
          {changeBadge('NDX', ctx.ndxChange)}
        </div>

        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          Sizing: <span className="font-medium text-[var(--foreground)]">{ctx.positionFactor === 1.0 ? '100%' : `${(ctx.positionFactor * 100).toFixed(0)}%`}</span>
        </Typography>

        {ctx.warning && <Chip label={ctx.warning} size="small" color="warning" variant="outlined" />}
      </div>
    </Paper>
  );
}
