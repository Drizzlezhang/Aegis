'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard' },
  { href: '/analyze', label: 'Analyze' },
  { href: '/history', label: 'History' },
  { href: '/status', label: 'Status' },
];

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-blue-400 hover:text-blue-300">
          <span className="inline-block h-6 w-6 rounded bg-blue-500" />
          Aegis-Trader
        </Link>
        <nav className="hidden items-center gap-5 text-sm font-medium text-slate-400 sm:flex">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`transition-colors ${active ? 'text-blue-400' : 'hover:text-slate-200'}`}
              >
                {item.label}
              </Link>
            );
          })}
          <span className="text-slate-700">|</span>
          <span className="text-xs text-slate-600">v0.1.0</span>
        </nav>
      </div>
    </header>
  );
}
