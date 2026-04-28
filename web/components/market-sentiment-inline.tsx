'use client';

import { Chip } from '@mui/material';
import { MarketIndexData } from '@/lib/api';
import { getChangeColorClasses } from '@/lib/change-color';
import { getSentimentStyle, getVixStyle, parseMarketContext } from '@/lib/market-context';

interface MarketSentimentInlineProps {
  indices: MarketIndexData[];
}

export default function MarketSentimentInline({ indices }: MarketSentimentInlineProps) {
  if (!indices || indices.length === 0) return null;

  const ctx = parseMarketContext(indices);
  const sentimentStyle = getSentimentStyle(ctx.sentiment);
  const spxChangeColors = ctx.spxChange !== null ? getChangeColorClasses(ctx.spxChange >= 0) : null;
  const ndxChangeColors = ctx.ndxChange !== null ? getChangeColorClasses(ctx.ndxChange >= 0) : null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 font-medium ${sentimentStyle.bg} ${sentimentStyle.text}`}>
        {sentimentStyle.label}
      </span>

      {ctx.vix !== null && (
        <span className={`font-medium ${getVixStyle(ctx.regime)}`}>
          VIX {ctx.vix.toFixed(2)}
        </span>
      )}

      {ctx.spxChange !== null && (
        <span className={spxChangeColors?.text}>
          SPX {ctx.spxChange >= 0 ? '+' : ''}{ctx.spxChange.toFixed(2)}%
        </span>
      )}

      {ctx.ndxChange !== null && (
        <span className={ndxChangeColors?.text}>
          NDX {ctx.ndxChange >= 0 ? '+' : ''}{ctx.ndxChange.toFixed(2)}%
        </span>
      )}

      {ctx.positionFactor !== 1.0 && <Chip label={`Sizing ${(ctx.positionFactor * 100).toFixed(0)}%`} size="small" color="warning" variant="outlined" />}

      {ctx.warning && <Chip label={ctx.warning} size="small" color="warning" variant="outlined" />}
    </div>
  );
}
