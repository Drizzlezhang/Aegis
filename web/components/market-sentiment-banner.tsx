'use client';

import { MarketIndexData } from '@/lib/api';

interface MarketSentimentBannerProps {
  indices: MarketIndexData[];
}

interface ParsedContext {
  vix: number | null;
  spxChange: number | null;
  ndxChange: number | null;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  regime: 'low' | 'normal' | 'elevated' | 'high';
  positionFactor: number;
  warning: string;
}

function parseMarketContext(indices: MarketIndexData[]): ParsedContext {
  let vix: number | null = null;
  let spxChange: number | null = null;
  let ndxChange: number | null = null;

  for (const idx of indices) {
    const sym = idx.symbol.toUpperCase();
    if (sym === '^VIX' || sym === 'VIX') vix = idx.price;
    if (sym === '^GSPC' || sym === 'SPX') spxChange = idx.change_percent;
    if (sym === '^IXIC' || sym === 'NDX') ndxChange = idx.change_percent;
  }

  // Volatility regime
  let regime: ParsedContext['regime'] = 'normal';
  let positionFactor = 1.0;
  let warning = '';

  if (vix !== null) {
    if (vix < 15) {
      regime = 'low';
    } else if (vix < 25) {
      regime = 'normal';
    } else if (vix < 30) {
      regime = 'elevated';
      positionFactor = 0.8;
      warning = 'VIX elevated — reduce position size';
    } else {
      regime = 'high';
      positionFactor = 0.5;
      warning = 'VIX high — significant risk-off, avoid new positions';
    }
  }

  // Sentiment
  let sentiment: ParsedContext['sentiment'] = 'neutral';
  if (spxChange !== null && ndxChange !== null) {
    const avg = (spxChange + ndxChange) / 2;
    if (avg > 1.0) sentiment = 'bullish';
    else if (avg < -1.0) sentiment = 'bearish';
  } else if (spxChange !== null) {
    if (spxChange > 1.0) sentiment = 'bullish';
    else if (spxChange < -1.0) sentiment = 'bearish';
  } else if (ndxChange !== null) {
    if (ndxChange > 1.5) sentiment = 'bullish';
    else if (ndxChange < -1.5) sentiment = 'bearish';
  }

  // NDX sharp drop warning
  if (ndxChange !== null && ndxChange < -2.0) {
    positionFactor = Math.min(positionFactor, 0.8);
    if (!warning) warning = 'NDX down >2% — tech weakness, exercise caution';
  }

  return { vix, spxChange, ndxChange, sentiment, regime, positionFactor, warning };
}

function sentimentBadge(sentiment: ParsedContext['sentiment']) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    bullish: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', label: 'Bullish' },
    bearish: { bg: 'bg-rose-500/10', text: 'text-rose-400', label: 'Bearish' },
    neutral: { bg: 'bg-slate-500/10', text: 'text-slate-400', label: 'Neutral' },
  };
  const s = map[sentiment];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

function vixBadge(vix: number | null, regime: ParsedContext['regime']) {
  if (vix === null) return <span className="text-xs text-slate-500">VIX: —</span>;
  const color: Record<string, string> = {
    low: 'text-emerald-400',
    normal: 'text-slate-300',
    elevated: 'text-amber-400',
    high: 'text-rose-400',
  };
  return (
    <span className={`text-xs font-medium ${color[regime]}`}>
      VIX: {vix.toFixed(2)}
    </span>
  );
}

function changeBadge(label: string, value: number | null) {
  if (value === null) return null;
  const isUp = value >= 0;
  const color = isUp ? 'text-emerald-400' : 'text-rose-400';
  return (
    <span className={`text-xs ${color}`}>
      {label}: {isUp ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}

export default function MarketSentimentBanner({ indices }: MarketSentimentBannerProps) {
  if (!indices || indices.length === 0) return null;

  const ctx = parseMarketContext(indices);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <div className="flex flex-wrap items-center gap-3">
        {/* Sentiment */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Market Sentiment</span>
          {sentimentBadge(ctx.sentiment)}
        </div>

        <div className="hidden h-4 w-px bg-slate-800 sm:block" />

        {/* VIX */}
        <div>{vixBadge(ctx.vix, ctx.regime)}</div>

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
