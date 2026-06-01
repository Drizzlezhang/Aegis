'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Box, Paper, Stack, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import type { SymbolInfo } from '@/lib/api';
import { getChangeColorClasses } from '@/lib/change-color';
import { useLocale } from './LocaleProvider';

const NAV_ITEMS = [
  { href: '/', key: 'common.dashboard' as const },
  { href: '/watchlist', key: 'common.watchlist' as const },
  { href: '/market', key: 'common.market' as const },
  { href: '/analyze', key: 'common.analyze' as const },
  { href: '/phase', key: 'common.phase' as const },
  { href: '/positions', key: 'common.positions' as const },
  { href: '/backtest', key: 'common.backtest' as const },
  { href: '/alerts', key: 'common.alerts' as const },
  { href: '/llm-cost', key: 'common.llmCost' as const },
  { href: '/history', key: 'common.history' as const },
  { href: '/scheduler', key: 'common.scheduler' as const },
  { href: '/tracking', key: 'common.tracking' as const },
  { href: '/memory', key: 'common.memory' as const },
  { href: '/status', key: 'common.status' as const },
  { href: '/settings', key: 'common.settings' as const },
];

interface SidebarProps {
  symbols?: SymbolInfo[];
}

export default function Sidebar({ symbols = [] }: SidebarProps) {
  const pathname = usePathname();
  const { locale } = useLocale();

  return (
    <aside className="hidden w-72 shrink-0 lg:block">
      <div className="sticky top-20 h-[calc(100vh-5rem)] overflow-y-auto px-4 pb-4">
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderRadius: '28px',
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <Typography variant="overline" sx={{ color: 'text.secondary', px: 1 }}>
            {getMessage(locale, 'common.navigation')}
          </Typography>
          <Stack spacing={1} sx={{ mb: 3, mt: 1 }}>
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Box
                  key={item.href}
                  component={Link}
                  href={item.href}
                  sx={{
                    px: 1.5,
                    py: 1.25,
                    borderRadius: '18px',
                    textDecoration: 'none',
                    fontSize: 14,
                    fontWeight: active ? 700 : 500,
                    color: active ? 'primary.contrastText' : 'text.primary',
                    backgroundColor: active ? 'primary.main' : 'transparent',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                >
                  {getMessage(locale, item.key)}
                </Box>
              );
            })}
          </Stack>

          <Typography variant="overline" sx={{ color: 'text.secondary', px: 1 }}>
            {getMessage(locale, 'common.watchlist')}
          </Typography>
          <Stack spacing={1} sx={{ mt: 1 }}>
            {symbols.map((s) => {
              const href = `/symbol/${s.symbol}`;
              const active = pathname === href;
              const positive = s.change >= 0;
              const changeColors = getChangeColorClasses(positive);
              return (
                <Box
                  key={s.symbol}
                  component={Link}
                  href={href}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 1,
                    px: 1.5,
                    py: 1.25,
                    borderRadius: '18px',
                    textDecoration: 'none',
                    color: active ? 'primary.contrastText' : 'text.primary',
                    backgroundColor: active ? 'primary.main' : 'transparent',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                >
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {s.symbol}
                  </Typography>
                  <span className={`text-xs font-semibold ${changeColors.text}`}>
                    {positive ? '+' : ''}
                    {s.changePercent.toFixed(2)}%
                  </span>
                </Box>
              );
            })}
          </Stack>
        </Paper>
      </div>
    </aside>
  );
}
