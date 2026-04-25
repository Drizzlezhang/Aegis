'use client';

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
  const colorClass = isUp ? 'text-emerald-400' : 'text-rose-400';
  const bgClass = isUp ? 'bg-emerald-500/10' : 'bg-rose-500/10';

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400">{name}</p>
          <p className="mt-1 text-lg font-bold text-slate-100">
            {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className={`flex items-center gap-1 rounded-full px-2 py-1 ${bgClass}`}>
          <span className={`text-xs ${colorClass}`}>{isUp ? '▲' : '▼'}</span>
          <span className={`text-xs font-medium ${colorClass}`}>
            {isUp ? '+' : ''}
            {change_percent.toFixed(2)}%
          </span>
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-500">{symbol}</p>
    </div>
  );
}
