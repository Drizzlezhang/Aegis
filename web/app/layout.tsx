import type { Metadata } from 'next';
import { LocaleProvider } from '@/components/LocaleProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Aegis-Trader Dashboard',
  description: 'Multi-Agent quantitative trading system dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-950 text-slate-200">
        <LocaleProvider initialLocale="zh-CN">{children}</LocaleProvider>
      </body>
    </html>
  );
}
