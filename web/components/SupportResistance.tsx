'use client';

import type { SupportResistance as SR } from '@/lib/mock-data';

interface SupportResistanceProps {
  supports: SR[];
  resistances: SR[];
  currentPrice: number;
}

export default function SupportResistance({ supports, resistances, currentPrice }: SupportResistanceProps) {
  const all = [
    ...supports.map((s) => ({ ...s, dist: ((currentPrice - s.level) / currentPrice) * 100 })),
    ...resistances.map((r) => ({ ...r, dist: ((r.level - currentPrice) / currentPrice) * 100 })),
  ].sort((a, b) => a.level - b.level);

  const minL = all[0]?.level ?? currentPrice * 0.8;
  const maxL = all[all.length - 1]?.level ?? currentPrice * 1.2;
  const range = maxL - minL || 1;

  return (
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-slate-300">Support / Resistance</h3>
      <div className="space-y-2">
        {all.map((item, i) => {
          const pct = ((item.level - minL) / range) * 100;
          const isSupport = item.type === 'support';
          return (
            <div key={i} className="relative">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2 w-2 rounded-full ${isSupport ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  <span className="font-medium text-slate-200">${item.level.toFixed(2)}</span>
                  <span className={`text-xs ${isSupport ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {isSupport ? 'S' : 'R'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{item.source}</span>
                  <StrengthBadge strength={item.strength} />
                  <span className="w-12 text-right text-xs text-slate-400">{item.dist.toFixed(1)}%</span>
                </div>
              </div>
              <div className="mt-1 h-1 w-full rounded-full bg-slate-800">
                <div
                  className={`h-1 rounded-full ${isSupport ? 'bg-emerald-500' : 'bg-rose-500'}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 rounded-lg bg-slate-800/50 p-2 text-center text-sm text-slate-400">
        Current: <span className="font-semibold text-slate-200">${currentPrice.toFixed(2)}</span>
      </div>
    </div>
  );
}

function StrengthBadge({ strength }: { strength: SR['strength'] }) {
  const map: Record<string, string> = {
    weak: 'badge-blue',
    moderate: 'badge-amber',
    strong: 'badge-green',
  };
  return <span className={map[strength] || 'badge-blue'}>{strength}</span>;
}
