'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
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
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';
import {
  getSchedulerStatus,
  triggerDailyAnalysis,
  triggerSingleAnalysis,
  type SchedulerStatusData,
} from '@/lib/api';

const DEFAULT_STATUS: SchedulerStatusData = {
  enabled: false,
  nextRunTime: null,
  isRunning: false,
  lastRunResults: [],
};

export default function SchedulerPage() {
  const { locale } = useLocale();
  const [status, setStatus] = useState<SchedulerStatusData>(DEFAULT_STATUS);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const [runningAll, setRunningAll] = useState(false);
  const [singleSymbol, setSingleSymbol] = useState('');
  const [runningSingle, setRunningSingle] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSchedulerStatus();
      setStatus(data);
      setUnavailable(false);
    } catch {
      setUnavailable(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRunAll = async () => {
    setRunningAll(true);
    try {
      await triggerDailyAnalysis();
      setMsg({ type: 'success', text: 'Analysis triggered successfully' });
      await load();
    } catch {
      setMsg({ type: 'error', text: 'Failed to trigger analysis' });
    } finally {
      setRunningAll(false);
    }
  };

  const handleAnalyzeSingle = async () => {
    const trimmed = singleSymbol.trim().toUpperCase();
    if (!trimmed) return;
    setRunningSingle(true);
    try {
      await triggerSingleAnalysis(trimmed);
      setMsg({ type: 'success', text: `Analysis triggered for ${trimmed}` });
      setSingleSymbol('');
      await load();
    } catch {
      setMsg({ type: 'error', text: 'Failed to trigger single analysis' });
    } finally {
      setRunningSingle(false);
    }
  };

  const formatTime = (iso: string | null): string => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  };

  return (
    <Box sx={{ p: { xs: 2, lg: 4 }, maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        {getMessage(locale, 'interaction.schedulerStatus')}
      </Typography>

      {msg && (
        <Alert severity={msg.type} onClose={() => setMsg(null)} sx={{ mb: 2 }}>
          {msg.text}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : unavailable ? (
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }} elevation={0} variant="outlined">
          <Typography variant="body1" color="text.secondary">
            {getMessage(locale, 'interaction.schedulerUnavailable')}
          </Typography>
        </Paper>
      ) : (
        <>
          <Paper sx={{ p: 3, mb: 3, borderRadius: 3 }} elevation={0} variant="outlined">
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              alignItems="center"
              justifyContent="space-between"
            >
              <Stack direction="row" spacing={2} alignItems="center">
                <Chip
                  label={
                    status.enabled
                      ? getMessage(locale, 'interaction.schedulerEnabled')
                      : getMessage(locale, 'interaction.schedulerDisabled')
                  }
                  color={status.enabled ? 'success' : 'default'}
                  size="small"
                />
                {status.isRunning && (
                  <Chip
                    icon={<CircularProgress size={14} />}
                    label={getMessage(locale, 'interaction.schedulerRunning')}
                    color="info"
                    size="small"
                  />
                )}
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {getMessage(locale, 'interaction.schedulerNextRun')}: {formatTime(status.nextRunTime)}
              </Typography>
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 2 }}>
              <Button
                variant="contained"
                startIcon={runningAll ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
                onClick={handleRunAll}
                disabled={runningAll || status.isRunning}
              >
                {getMessage(locale, 'interaction.schedulerRunAll')}
              </Button>

              <Stack direction="row" spacing={1}>
                <TextField
                  label={getMessage(locale, 'interaction.watchlistSymbol')}
                  value={singleSymbol}
                  onChange={(e) => setSingleSymbol(e.target.value)}
                  size="small"
                  sx={{ width: 160 }}
                />
                <Button
                  variant="outlined"
                  onClick={handleAnalyzeSingle}
                  disabled={runningSingle || !singleSymbol.trim()}
                >
                  {runningSingle ? (
                    <CircularProgress size={16} />
                  ) : (
                    getMessage(locale, 'interaction.schedulerAnalyzeSingle')
                  )}
                </Button>
              </Stack>
            </Stack>
          </Paper>

          <Typography variant="h6" sx={{ mb: 2 }}>
            {getMessage(locale, 'interaction.schedulerLastResults')}
          </Typography>

          {status.lastRunResults.length === 0 ? (
            <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 3 }} elevation={0} variant="outlined">
              <Typography variant="body2" color="text.secondary">
                {getMessage(locale, 'interaction.pipeline_no_data')}
              </Typography>
            </Paper>
          ) : (
            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>{getMessage(locale, 'interaction.watchlistSymbol')}</TableCell>
                    <TableCell>{getMessage(locale, 'common.status')}</TableCell>
                    <TableCell>{getMessage(locale, 'interaction.schedulerRecommendations')}</TableCell>
                    <TableCell>{getMessage(locale, 'interaction.elapsed_time')}</TableCell>
                    <TableCell>{getMessage(locale, 'interaction.schedulerTraceId')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {status.lastRunResults.map((r, i) => (
                    <TableRow key={r.traceId || i} hover>
                      <TableCell>
                        <Typography fontWeight={700}>{r.symbol}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={
                            r.success
                              ? getMessage(locale, 'interaction.schedulerSuccess')
                              : getMessage(locale, 'interaction.schedulerFailed')
                          }
                          color={r.success ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{r.recommendationsCount}</TableCell>
                      <TableCell>{r.executionTime}s</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace" color="text.secondary">
                          {r.traceId?.slice(0, 12)}...
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </>
      )}
    </Box>
  );
}