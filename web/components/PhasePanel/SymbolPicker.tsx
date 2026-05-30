'use client';

import { Autocomplete, TextField } from '@mui/material';
import type { SymbolInfo } from '@/lib/api';

interface SymbolPickerProps {
  symbols: SymbolInfo[];
  selected: string;
  onSelect: (symbol: string) => void;
}

export function SymbolPicker({ symbols, selected, onSelect }: SymbolPickerProps) {
  return (
    <Autocomplete
      size="small"
      options={symbols}
      getOptionLabel={(s) => `${s.symbol} — ${s.name}`}
      value={symbols.find((s) => s.symbol === selected) ?? null}
      onChange={(_, v) => v && onSelect(v.symbol)}
      renderInput={(params) => (
        <TextField {...params} label="选择标的" placeholder="搜索..." />
      )}
      sx={{ minWidth: 260 }}
    />
  );
}
