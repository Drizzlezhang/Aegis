'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import { AppBar, Box, Chip, IconButton, Stack, Toolbar, Tooltip, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import { useThemeMode } from '@/components/theme/AppThemeProvider';
import { useLocale } from './LocaleProvider';
import LocaleSwitcher from './LocaleSwitcher';
import NotificationCenter from './NotificationCenter';

const NAV_ITEMS = [
  { href: '/', key: 'common.dashboard' as const },
  { href: '/analyze', key: 'common.analyze' as const },
  { href: '/history', key: 'common.history' as const },
  { href: '/status', key: 'common.status' as const },
];

export default function Header() {
  const pathname = usePathname();
  const { locale } = useLocale();
  const { mode, toggleMode } = useThemeMode();

  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      sx={{
        backdropFilter: 'blur(18px)',
        backgroundColor: 'color-mix(in srgb, var(--surface) 84%, transparent)',
        borderBottom: '1px solid var(--outline)',
      }}
    >
      <Toolbar sx={{ mx: 'auto', width: '100%', maxWidth: 1280, gap: 2, px: { xs: 2, md: 3 } }}>
        <Link href="/" className="no-underline">
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: '14px',
                background: 'linear-gradient(135deg, var(--primary-main) 0%, var(--primary-hover) 100%)',
                boxShadow: '0 10px 24px var(--primary-soft)',
              }}
            />
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, lineHeight: 1.1, color: 'text.primary' }}>
                Aegis-Trader
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                Material dashboard
              </Typography>
            </Box>
          </Stack>
        </Link>

        <Stack direction="row" spacing={1} alignItems="center" sx={{ ml: 3, flex: 1, display: { xs: 'none', sm: 'flex' } }}>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className="no-underline">
                <Chip
                  label={getMessage(locale, item.key)}
                  clickable
                  color={active ? 'primary' : 'default'}
                  variant={active ? 'filled' : 'outlined'}
                  sx={{
                    borderRadius: '999px',
                    fontWeight: 600,
                    ...(active
                      ? {
                          bgcolor: 'primary.main',
                          color: 'primary.contrastText',
                          borderColor: 'primary.main',
                          '& .MuiChip-label': {
                            color: 'inherit',
                          },
                        }
                      : {}),
                  }}
                />
              </Link>
            );
          })}
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center">
          <NotificationCenter />
          <LocaleSwitcher />
          <Tooltip title={mode === 'dark' ? '切换到浅色模式' : '切换到深色模式'}>
            <IconButton
              aria-label={mode === 'dark' ? 'switch to light mode' : 'switch to dark mode'}
              onClick={toggleMode}
              sx={{
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': { bgcolor: 'action.hover' },
              }}
            >
              {mode === 'dark' ? <LightModeRoundedIcon /> : <DarkModeRoundedIcon />}
            </IconButton>
          </Tooltip>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: { xs: 'none', md: 'block' } }}>
            v0.1.0
          </Typography>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
