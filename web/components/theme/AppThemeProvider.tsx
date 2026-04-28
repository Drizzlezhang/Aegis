'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import type { ThemeMode } from '@/lib/theme/theme-storage';
import { resolveInitialThemeMode, writeStoredThemeMode } from '@/lib/theme/theme-storage';

const STORAGE_ATTR = 'data-theme';

type ThemeModeContextValue = {
  mode: ThemeMode;
  toggleMode: () => void;
};

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#6750A4' },
    secondary: { main: '#625B71' },
    background: { default: '#f5f1fb', paper: '#ffffff' },
    text: { primary: '#1d1b20', secondary: '#49454f' },
    success: { main: '#2e7d32' },
    error: { main: '#b3261e' },
    warning: { main: '#b26a00' },
  },
  shape: { borderRadius: 20 },
  typography: {
    fontFamily: 'Roboto, "Noto Sans SC", "Segoe UI", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#d0bcff' },
    secondary: { main: '#ccc2dc' },
    background: { default: '#0f0d13', paper: '#17151c' },
    text: { primary: '#f5eff7', secondary: '#cac4d0' },
    success: { main: '#10b981' },
    error: { main: '#f2b8b5' },
    warning: { main: '#f4bf50' },
  },
  shape: { borderRadius: 20 },
  typography: {
    fontFamily: 'Roboto, "Noto Sans SC", "Segoe UI", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    h3: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>('dark');

  useEffect(() => {
    setMode(resolveInitialThemeMode());
  }, []);

  useEffect(() => {
    writeStoredThemeMode(mode);
    document.documentElement.setAttribute(STORAGE_ATTR, mode);
  }, [mode]);

  const value = useMemo(
    () => ({
      mode,
      toggleMode: () => setMode((current) => (current === 'dark' ? 'light' : 'dark')),
    }),
    [mode],
  );

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={mode === 'dark' ? darkTheme : lightTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

export function useThemeMode() {
  const value = useContext(ThemeModeContext);
  if (!value) {
    throw new Error('useThemeMode must be used within AppThemeProvider');
  }
  return value;
}
