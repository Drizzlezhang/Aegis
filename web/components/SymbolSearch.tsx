'use client';

import { useMemo, useState, type KeyboardEvent } from 'react';
import { Button, Chip, Paper, TextField, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import { interpolate } from '@/i18n/interpolate';
import { useLocale } from './LocaleProvider';

type SymbolSearchProps = {
  selected: string[];
  onChange: (symbols: string[]) => void;
  maxSymbols?: number;
  disabled?: boolean;
};

const POPULAR_SYMBOLS = ['QQQ', 'SPY', 'NVDA', 'MSFT', 'AAPL', 'PLTR', 'NFLX', 'INTC', 'TSM', 'TSLA', 'KO'];

function normalizeSymbol(raw: string): string {
  return raw.trim().toUpperCase();
}

function tokenizeInput(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => normalizeSymbol(item))
    .filter(Boolean);
}

export default function SymbolSearch({ selected, onChange, maxSymbols = 20, disabled = false }: SymbolSearchProps) {
  const { locale } = useLocale();
  const [input, setInput] = useState('');

  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const canAddMore = selected.length < maxSymbols;

  const addSymbols = (symbols: string[]) => {
    if (symbols.length === 0 || !canAddMore) return;

    const next = [...selected];
    for (const symbol of symbols) {
      if (next.length >= maxSymbols) break;
      if (!selectedSet.has(symbol) && !next.includes(symbol)) {
        next.push(symbol);
      }
    }
    onChange(next);
  };

  const removeSymbol = (symbol: string) => {
    onChange(selected.filter((item) => item !== symbol));
  };

  const handleSubmitInput = () => {
    addSymbols(tokenizeInput(input));
    setInput('');
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      handleSubmitInput();
    }
  };

  return (
    <Paper elevation={0} className="card">
      <div className="mb-2 flex items-center justify-between">
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.symbol_search_popular')}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          {interpolate(getMessage(locale, 'interaction.analyze_button'), { count: selected.length })}
        </Typography>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {POPULAR_SYMBOLS.map((symbol) => {
          const active = selectedSet.has(symbol);
          return (
            <Button
              key={symbol}
              size="small"
              variant={active ? 'contained' : 'outlined'}
              disabled={disabled || (!active && !canAddMore)}
              onClick={() => addSymbols([symbol])}
              sx={{ borderRadius: '999px', minWidth: 0, px: 1.5 }}
            >
              {symbol}
            </Button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <TextField
          size="small"
          fullWidth
          value={input}
          disabled={disabled || !canAddMore}
          placeholder={getMessage(locale, 'interaction.symbol_search_placeholder')}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleInputKeyDown}
        />
        <Button
          size="small"
          variant="outlined"
          disabled={disabled || !canAddMore || input.trim().length === 0}
          onClick={handleSubmitInput}
        >
          {getMessage(locale, 'interaction.symbol_search_add')}
        </Button>
      </div>

      {!canAddMore && (
        <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'warning.main' }}>
          {interpolate(getMessage(locale, 'interaction.symbol_search_max_reached'), { max: maxSymbols })}
        </Typography>
      )}

      {selected.length > 0 && (
        <div className="mt-3">
          <div className="mb-2 flex items-center justify-between">
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {interpolate(getMessage(locale, 'interaction.analyze_button'), { count: selected.length })}
            </Typography>
            <Button size="small" disabled={disabled} onClick={() => onChange([])}>
              {getMessage(locale, 'interaction.symbol_search_clear_all')}
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {selected.map((symbol) => (
              <Chip key={symbol} label={symbol} onDelete={disabled ? undefined : () => removeSymbol(symbol)} size="small" />
            ))}
          </div>
        </div>
      )}
    </Paper>
  );
}
