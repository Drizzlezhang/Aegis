'use client';

import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import { useThemeMode } from '@/components/theme/AppThemeProvider';
import { getMessage } from '@/i18n/get-message';
import type { Locale } from '@/i18n/types';

interface ThemeToggleProps {
  locale?: Locale;
}

export function ThemeToggle({ locale = 'zh-CN' }: ThemeToggleProps) {
  const { mode, toggleMode } = useThemeMode();

  const isLight = mode === 'light';

  return (
    <Tooltip title={isLight ? getMessage(locale, 'interaction.themeDark') : getMessage(locale, 'interaction.themeLight')}>
      <IconButton onClick={toggleMode} size="small" aria-label="toggle theme">
        {isLight ? <DarkModeIcon /> : <LightModeIcon />}
      </IconButton>
    </Tooltip>
  );
}
