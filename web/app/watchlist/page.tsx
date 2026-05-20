'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Chip,
  IconButton,
  Paper,
  Select,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';
import {
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  type WatchlistItem,
} from '@/lib/api';

const PRIORITY_COLORS: Record<number, 'error' | 'warning' | 'success' | 'info' | 'default'> = {
  1: 'error',
  2: 'warning',
  3: 'info',
  4: 'default',
  5: 'default',
};

export default function WatchlistPage() {
  const { locale } = useLocale();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState('');
  const [priority, setPriority] = useState(3);
  const [notes, setNotes] = useState('');
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWatchlist();
      setItems(data.sort((a, b) => a.priority - b.priority));
    } catch {
      setError('Failed to load watchlist');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed) return;

    const duplicate = items.find((i) => i.symbol === trimmed);
    if (duplicate) {
      setMsg({ type: 'error', text: getMessage(locale, 'interaction.watchlistDuplicate') });
      return;
    }

    setAdding(true);
    try {
      const item = await addToWatchlist(trimmed, notes || undefined, priority);
      setItems((prev) =>
        [...prev, item].sort((a, b) => a.priority - b.priority)
      );
      setSymbol('');
      setNotes('');
      setPriority(3);
      setMsg(null);
    } catch {
      setMsg({ type: 'error', text: 'Failed to add symbol' });
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (s: string) => {
    try {
      await removeFromWatchlist(s);
      setItems((prev) => prev.filter((i) => i.symbol !== s));
    } catch {
      setMsg({ type: 'error', text: 'Failed to remove symbol' });
    }
  };

  return (
    <Box sx={{ p: { xs: 2, lg: 4 }, maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        {getMessage(locale, 'common.watchlist')}
      </Typography>

      {msg && (
        <Alert severity={msg.type} onClose={() => setMsg(null)} sx={{ mb: 2 }}>
          {msg.text}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 3, borderRadius: 3 }} elevation={0} variant="outlined">
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'flex-end' }}>
          <TextField
            label={getMessage(locale, 'interaction.watchlistSymbol')}
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            size="small"
            sx={{ minWidth: 140 }}
          />
          <Box sx={{ minWidth: 100 }}>
            <Typography variant="caption" color="text.secondary">
              {getMessage(locale, 'interaction.watchlistPriority')}
            </Typography>
            <Select
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              size="small"
              fullWidth
            >
              {[1, 2, 3, 4, 5].map((p) => (
                <MenuItem key={p} value={p}>
                  {p} {p === 1 ? `(${getMessage(locale, 'interaction.watchlistPriorityHigh')})` : ''}
                </MenuItem>
              ))}
            </Select>
          </Box>
          <TextField
            label={getMessage(locale, 'interaction.watchlistNotes')}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            size="small"
            sx={{ flex: 1, minWidth: 140 }}
          />
          <Button
            variant="contained"
            onClick={handleAdd}
            disabled={adding || !symbol.trim()}
            sx={{ height: 40, px: 3 }}
          >
            {adding ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              getMessage(locale, 'interaction.watchlistAdd')
            )}
          </Button>
        </Stack>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : items.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }} elevation={0} variant="outlined">
          <Typography variant="body1" color="text.secondary">
            {getMessage(locale, 'interaction.watchlistEmpty')}
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{getMessage(locale, 'interaction.watchlistSymbol')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.watchlistPriority')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.watchlistNotes')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.watchlistAddedAt')}</TableCell>
                <TableCell align="right">{getMessage(locale, 'interaction.watchlistRemove')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.symbol} hover>
                  <TableCell>
                    <Typography fontWeight={700}>{item.symbol}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={item.priority}
                      color={PRIORITY_COLORS[item.priority] ?? 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
                      {item.notes || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(item.addedAt).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleRemove(item.symbol)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}