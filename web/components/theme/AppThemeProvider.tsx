'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { CssBaseline, ThemeProvider } from '@mui/material';
import { alpha, createTheme } from '@mui/material/styles';
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
    primary: { main: '#4285f4', contrastText: '#ffffff' },
    secondary: { main: '#5f6b7a' },
    background: { default: '#f6f9fc', paper: '#ffffff' },
    text: { primary: '#1f2a37', secondary: '#5f6b7a' },
    divider: 'rgba(92, 122, 153, 0.18)',
    success: { main: '#2e7d32' },
    error: { main: '#c53929' },
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
          border: '1px solid rgba(92, 122, 153, 0.18)',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(92, 122, 153, 0.18)',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(92, 122, 153, 0.3)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#4285f4',
            borderWidth: 1,
          },
          '&.Mui-focused': {
            boxShadow: `0 0 0 2px ${alpha('#4285f4', 0.14)}`,
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          '&.MuiButton-outlined': {
            borderColor: 'rgba(92, 122, 153, 0.18)',
          },
          '&.MuiButton-outlined:hover': {
            borderColor: 'rgba(92, 122, 153, 0.3)',
            backgroundColor: 'rgba(66, 133, 244, 0.08)',
          },
          '&.MuiButton-text:hover': {
            backgroundColor: 'rgba(66, 133, 244, 0.08)',
          },
          '&.Mui-focusVisible': {
            boxShadow: `0 0 0 2px ${alpha('#4285f4', 0.14)}`,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: '#eef3f9',
          border: '1px solid rgba(92, 122, 153, 0.18)',
          '&:hover': {
            backgroundColor: alpha('#4285f4', 0.08),
            borderColor: 'rgba(92, 122, 153, 0.3)',
          },
          '&.Mui-focusVisible': {
            boxShadow: `0 0 0 2px ${alpha('#4285f4', 0.14)}`,
          },
        },
        filledPrimary: {
          backgroundColor: '#4285f4',
          color: '#ffffff',
          borderColor: '#4285f4',
          '& .MuiChip-label': {
            color: 'inherit',
          },
          '&:hover': {
            backgroundColor: '#336fd1',
            color: '#ffffff',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(92, 122, 153, 0.18)',
        },
        head: {
          backgroundColor: '#eef3f9',
        },
      },
    },
  },
});

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#8ab4f8', contrastText: '#0f1722' },
    secondary: { main: '#a8b6c7' },
    background: { default: '#0f1722', paper: '#17212d' },
    text: { primary: '#edf3fb', secondary: '#a8b6c7' },
    divider: 'rgba(168, 182, 199, 0.16)',
    success: { main: '#81c995' },
    error: { main: '#f28b82' },
    warning: { main: '#fbc02d' },
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
          border: '1px solid rgba(168, 182, 199, 0.16)',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: '#17212d',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(168, 182, 199, 0.16)',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(168, 182, 199, 0.28)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#8ab4f8',
            borderWidth: 1,
          },
          '&.Mui-focused': {
            boxShadow: `0 0 0 2px ${alpha('#8ab4f8', 0.18)}`,
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          '&.MuiButton-outlined': {
            borderColor: 'rgba(168, 182, 199, 0.16)',
          },
          '&.MuiButton-outlined:hover': {
            borderColor: 'rgba(168, 182, 199, 0.28)',
            backgroundColor: 'rgba(138, 180, 248, 0.1)',
          },
          '&.MuiButton-text:hover': {
            backgroundColor: 'rgba(138, 180, 248, 0.1)',
          },
          '&.Mui-focusVisible': {
            boxShadow: `0 0 0 2px ${alpha('#8ab4f8', 0.18)}`,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: '#1d2936',
          border: '1px solid rgba(168, 182, 199, 0.16)',
          '&:hover': {
            backgroundColor: alpha('#8ab4f8', 0.1),
            borderColor: 'rgba(168, 182, 199, 0.28)',
          },
          '&.Mui-focusVisible': {
            boxShadow: `0 0 0 2px ${alpha('#8ab4f8', 0.18)}`,
          },
        },
        filledPrimary: {
          backgroundColor: '#8ab4f8',
          color: '#0f1722',
          borderColor: '#8ab4f8',
          '& .MuiChip-label': {
            color: 'inherit',
          },
          '&:hover': {
            backgroundColor: '#a8c7fa',
            color: '#0f1722',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(168, 182, 199, 0.16)',
        },
        head: {
          backgroundColor: '#1d2936',
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
