import type { Metadata } from 'next';
import { LocaleProvider } from '@/components/LocaleProvider';
import { AppThemeProvider } from '@/components/theme/AppThemeProvider';
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
          <LocaleProvider initialLocale="zh-CN">{children}</LocaleProvider>
        </AppThemeProvider>
      </body>
    </html>
  );
}
