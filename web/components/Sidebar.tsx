'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SYMBOLS } from '@/lib/mock-data';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-800 bg-slate-900/50 lg:block">
      <div className="sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto p-3">
        <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Watchlist
        </h2>
        <ul className="space-y-1">
          {SYMBOLS.map((s) => {
            const href = `/symbol/${s.symbol}`;
            const active = pathname === href;
            const positive = s.change >= 0;
            return (
              <li key={s.symbol}>
                <Link
                  href={href}
                  className={`flex items-center justify-between rounded-lg px-2 py-1.5 text-sm transition-colors ${
                    active
                      ? 'bg-blue-950/50 text-blue-300'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <span className="font-medium">{s.symbol}</span>
                  <span className={`text-xs ${positive ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {positive ? '+' : ''}
                    {s.changePercent.toFixed(2)}%
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
