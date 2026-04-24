'use client';

import Link from 'next/link';
import type { SymbolInfo } from '@/lib/mock-data';

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

  return (
    <Link
      href={`/symbol/${symbol.symbol}`}
      className="card hover:border-slate-700 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-100">{symbol.symbol}</h3>
          <p className="text-xs text-slate-500">{symbol.name}</p>
        </div>
        <StatusBadge status={symbol.analysisStatus} />
      </div>

      <div className="mt-3 flex items-end justify-between">
        <div>
          <p className="text-2xl font-semibold text-slate-100">
            ${symbol.price.toFixed(2)}
          </p>
          <p className={`text-sm font-medium ${positive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {positive ? '+' : ''}
            {symbol.change.toFixed(2)} ({positive ? '+' : ''}
            {symbol.changePercent.toFixed(2)}%)
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Vol</p>
          <p className="text-sm font-medium text-slate-300">{formatVolume(symbol.volume)}</p>
        </div>
      </div>

      <div className="mt-3">
        <TrendIndicator trend={symbol.trend} />
      </div>
    </Link>
  );
}

function StatusBadge({ status }: { status: SymbolInfo['analysisStatus'] }) {
  if (status === 'completed') return <span className="badge-green">Done</span>;
  if (status === 'pending') return <span className="badge-amber">Pending</span>;
  return <span className="badge-red">Error</span>;
}

function TrendIndicator({ trend }: { trend: SymbolInfo['trend'] }) {
  const bars = [
    { label: 'Bearish', active: trend === 'down', color: 'bg-rose-500' },
    { label: 'Neutral', active: trend === 'neutral', color: 'bg-amber-500' },
    { label: 'Bullish', active: trend === 'up', color: 'bg-emerald-500' },
  ];

  return (
    <div className="flex gap-1">
      {bars.map((b) => (
        <div
          key={b.label}
          className={`h-1.5 flex-1 rounded-full ${b.active ? b.color : 'bg-slate-800'}`}
          title={b.label}
        />
      ))}
    </div>
  );
}
