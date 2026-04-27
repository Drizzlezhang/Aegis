'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getMessage } from '@/i18n/get-message';
import type { SymbolInfo } from '@/lib/api';
import { getChangeColorClasses } from '@/lib/change-color';
import { useLocale } from './LocaleProvider';

const NAV_ITEMS = [
  { href: '/', key: 'common.dashboard' as const },
  { href: '/market', key: 'common.market' as const },
  { href: '/analyze', key: 'common.analyze' as const },
  { href: '/backtest', key: 'common.backtest' as const },
  { href: '/history', key: 'common.history' as const },
  { href: '/memory', key: 'common.memory' as const },
  { href: '/status', key: 'common.status' as const },
];

interface SidebarProps {
  symbols?: SymbolInfo[];
}

export default function Sidebar({ symbols = [] }: SidebarProps) {
  const pathname = usePathname();
  const { locale } = useLocale();

  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-800 bg-slate-900/50 lg:block">
      <div className="sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto p-3">
        <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          {getMessage(locale, 'common.navigation')}
        </h2>
        <ul className="mb-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`block rounded-lg px-2 py-1.5 text-sm transition-colors ${
                    active
                      ? 'bg-blue-950/50 text-blue-300'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {getMessage(locale, item.key)}
                </Link>
              </li>
            );
          })}
        </ul>

        <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          {getMessage(locale, 'common.watchlist')}
        </h2>
        <ul className="space-y-1">
          {symbols.map((s) => {
            const href = `/symbol/${s.symbol}`;
            const active = pathname === href;
            const positive = s.change >= 0;
            const changeColors = getChangeColorClasses(positive);
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
                  <span className={`text-xs ${changeColors.text}`}>
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
