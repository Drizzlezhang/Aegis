'use client';

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
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400">{name}</p>
          <p className="mt-1 text-lg font-bold text-slate-100">
            {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className={`flex items-center gap-1 rounded-full px-2 py-1 ${changeColors.bg}`}>
          <span className={`text-xs ${changeColors.text}`}>{isUp ? '▲' : '▼'}</span>
          <span className={`text-xs font-medium ${changeColors.text}`}>
            {isUp ? '+' : ''}
            {change_percent.toFixed(2)}%
          </span>
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">{symbol}</p>
    </div>
  );
}
