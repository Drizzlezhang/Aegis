'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Chip, Paper, Stack, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import { getPositionAlerts, type PositionAlertData } from '@/lib/api';
import { useLocale } from './LocaleProvider';

const severityRank: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

const severityColorMap: Record<string, 'error' | 'warning' | 'info' | 'default'> = {
  critical: 'error',
  warning: 'warning',
  info: 'info',
};

export default function AlertsPanel() {
  const { locale } = useLocale();
  const [alerts, setAlerts] = useState<PositionAlertData[]>([]);
  const [scannedAt, setScannedAt] = useState<string>('');
  const [loading, setLoading] = useState(true);

  const loadAlerts = useCallback(async () => {
    try {
      const resp = await getPositionAlerts();
      setAlerts(resp.alerts);
      setScannedAt(resp.scanned_at);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAlerts();
    const timer = setInterval(() => {
      void loadAlerts();
    }, 30000);
    return () => {
      clearInterval(timer);
    };
  }, [loadAlerts]);

  const sortedAlerts = useMemo(() => {
    return [...alerts].sort((a, b) => (severityRank[a.severity] ?? 99) - (severityRank[b.severity] ?? 99));
  }, [alerts]);

  return (
    <Paper elevation={0} className="card">
      <div className="mb-3 flex items-center justify-between gap-3">
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.position_alerts_title')}
        </Typography>
        <Chip label={String(sortedAlerts.length)} size="small" variant="outlined" />
      </div>

      {scannedAt && (
        <Typography variant="caption" sx={{ display: 'block', mb: 2, color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.alerts_last_scanned')}: {new Date(scannedAt).toLocaleString()}
        </Typography>
      )}

      {loading ? (
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.alerts_loading')}
        </Typography>
      ) : sortedAlerts.length === 0 ? (
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.alerts_empty')}
        </Typography>
      ) : (
        <Stack spacing={1.5}>
          {sortedAlerts.map((alert) => (
            <Paper key={`${alert.position_id}-${alert.type}-${alert.message}`} elevation={0} className="card-muted">
              <div className="flex items-center justify-between gap-3">
                <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                  {alert.symbol}
                </Typography>
                <Chip
                  label={alert.severity}
                  size="small"
                  color={severityColorMap[alert.severity] ?? 'default'}
                  variant="filled"
                  sx={{ textTransform: 'capitalize', borderRadius: '999px', fontWeight: 700 }}
                />
              </div>
              <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                {alert.message}
              </Typography>
              <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'text.secondary' }}>
                {alert.suggested_action}
              </Typography>
            </Paper>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
