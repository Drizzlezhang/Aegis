'use client';

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
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <div className="flex flex-wrap items-center gap-3">
        {/* Sentiment */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Market Sentiment</span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${sentimentStyle.bg} ${sentimentStyle.text}`}>
            {sentimentStyle.label}
          </span>
        </div>

        <div className="hidden h-4 w-px bg-slate-800 sm:block" />

        {/* VIX */}
        <div>
          {ctx.vix !== null ? (
            <span className={`text-xs font-medium ${getVixStyle(ctx.regime)}`}>
              VIX: {ctx.vix.toFixed(2)}
            </span>
          ) : (
            <span className="text-xs text-slate-500">VIX: —</span>
          )}
        </div>

        <div className="hidden h-4 w-px bg-slate-800 sm:block" />

        {/* Index changes */}
        <div className="flex items-center gap-3">
          {changeBadge('SPX', ctx.spxChange)}
          {changeBadge('NDX', ctx.ndxChange)}
        </div>

        <div className="hidden h-4 w-px bg-slate-800 sm:block" />

        {/* Position sizing */}
        <div className="text-xs text-slate-400">
          Sizing: <span className="font-medium text-slate-200">{ctx.positionFactor === 1.0 ? '100%' : `${(ctx.positionFactor * 100).toFixed(0)}%`}</span>
        </div>

        {/* Warning */}
        {ctx.warning && (
          <>
            <div className="hidden h-4 w-px bg-slate-800 sm:block" />
            <span className="text-xs font-medium text-amber-400">
              {ctx.warning}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
