'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import BacktestHistoryTable from '@/components/BacktestHistoryTable';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { useLocale } from '@/components/LocaleProvider';
import { getMessage } from '@/i18n/get-message';
import {
  deleteBacktestRun,
  getBacktestHistory,
  getSymbols,
  type BacktestRunSummary,
  type SymbolInfo,
} from '@/lib/api';

export default function BacktestHistoryPage() {
  const { locale } = useLocale();
  const [runs, setRuns] = useState<BacktestRunSummary[]>([]);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const fetchRuns = useCallback(async (symbol?: string) => {
    setLoading(true);
    try {
      const data = await getBacktestHistory(symbol || undefined);
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
    getSymbols().then(setSymbols).catch(() => setSymbols([]));
  }, [fetchRuns]);

  const handleFilter = () => {
    fetchRuns(filterSymbol.trim() || undefined);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    const ok = await deleteBacktestRun(deleteTarget);
    setDeleteTarget(null);
    if (ok) {
      setSnackbar('Deleted');
      fetchRuns(filterSymbol.trim() || undefined);
    }
  };

  const handleSelect = (runId: string) => {
    // Navigate to detail or expand — for now just show snackbar
    setSnackbar(`Selected run: ${runId}`);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <Stack spacing={3}>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                {getMessage(locale, 'backtestHistoryPage.title')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {getMessage(locale, 'backtestHistoryPage.subtitle')}
              </Typography>
            </Box>

            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                size="small"
                placeholder={getMessage(locale, 'backtestHistoryPage.filterSymbol')}
                value={filterSymbol}
                onChange={(e) => setFilterSymbol(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleFilter()}
                sx={{ width: 200 }}
              />
              <Button variant="outlined" size="small" onClick={handleFilter}>
                {getMessage(locale, 'common.search')}
              </Button>
            </Stack>

            {loading ? (
              <Typography color="text.secondary">{getMessage(locale, 'common.loading')}...</Typography>
            ) : (
              <BacktestHistoryTable
                runs={runs}
                onSelect={handleSelect}
                onDelete={(id) => setDeleteTarget(id)}
              />
            )}
          </Stack>
        </main>
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>{getMessage(locale, 'backtestHistoryPage.delete')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {getMessage(locale, 'backtestHistoryPage.deleteConfirm')}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>
            {getMessage(locale, 'common.error')}
          </Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            {getMessage(locale, 'backtestHistoryPage.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={3000}
        onClose={() => setSnackbar(null)}
        message={snackbar}
      />
    </div>
  );
}
