import type { Metadata } from 'next';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { LocaleProvider } from '@/components/LocaleProvider';
import { AppThemeProvider } from '@/components/theme/AppThemeProvider';
import PushBanner from '@/components/PushBanner';
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
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="min-h-screen">
        <AppThemeProvider>
          <LocaleProvider initialLocale="zh-CN">
            <PushBanner />
            <ErrorBoundary>{children}</ErrorBoundary>
          </LocaleProvider>
        </AppThemeProvider>
      </body>
    </html>
  );
}
