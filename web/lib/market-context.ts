import { MarketIndexData } from './api';

export interface ParsedMarketContext {
  vix: number | null;
  spxChange: number | null;
  ndxChange: number | null;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  regime: 'low' | 'normal' | 'elevated' | 'high';
  positionFactor: number;
  warning: string;
}

export function parseMarketContext(indices: MarketIndexData[]): ParsedMarketContext {
  let vix: number | null = null;
  let spxChange: number | null = null;
  let ndxChange: number | null = null;

  for (const idx of indices) {
    const sym = idx.symbol.toUpperCase();
    if (sym === '^VIX' || sym === 'VIX') vix = idx.price;
    if (sym === '^GSPC' || sym === 'SPX') spxChange = idx.change_percent;
    if (sym === '^IXIC' || sym === 'NDX') ndxChange = idx.change_percent;
  }

  let regime: ParsedMarketContext['regime'] = 'normal';
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

  let sentiment: ParsedMarketContext['sentiment'] = 'neutral';
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

  if (ndxChange !== null && ndxChange < -2.0) {
    positionFactor = Math.min(positionFactor, 0.8);
    if (!warning) warning = 'NDX down >2% — tech weakness, exercise caution';
  }

  return { vix, spxChange, ndxChange, sentiment, regime, positionFactor, warning };
}

export function getSentimentStyle(sentiment: ParsedMarketContext['sentiment']) {
  const map = {
    bullish: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', label: 'Bullish' },
    bearish: { bg: 'bg-rose-500/10', text: 'text-rose-400', label: 'Bearish' },
    neutral: { bg: 'bg-slate-500/10', text: 'text-slate-400', label: 'Neutral' },
  };
  return map[sentiment];
}

export function getVixStyle(regime: ParsedMarketContext['regime']) {
  const map = {
    low: 'text-emerald-400',
    normal: 'text-slate-300',
    elevated: 'text-amber-400',
    high: 'text-rose-400',
  };
  return map[regime];
}
