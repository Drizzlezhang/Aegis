'use client';

import Link from 'next/link';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-blue-400 hover:text-blue-300">
          <span className="inline-block h-6 w-6 rounded bg-blue-500" />
          Aegis-Trader
        </Link>
        <nav className="flex items-center gap-6 text-sm font-medium text-slate-400">
          <Link href="/" className="hover:text-slate-200">Dashboard</Link>
          <span className="text-slate-700">|</span>
          <span className="text-xs text-slate-600">v0.1.0</span>
        </nav>
      </div>
    </header>
  );
}
