'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Box, Card, CardContent, Typography, Chip, Stack } from '@mui/material';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getMessage } from '@/i18n/get-message';
import type { Locale } from '@/i18n/types';

interface PriceData {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: number;
}

interface RealtimeTickerProps {
  symbols: string[];
  wsUrl?: string | null;
  showVolume?: boolean;
  locale?: Locale;
}

export function RealtimeTicker({ symbols, wsUrl = null, showVolume = false, locale = 'zh-CN' }: RealtimeTickerProps) {
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [flashSymbol, setFlashSymbol] = useState<string | null>(null);

  const effectiveWsUrl = useMemo(() => {
    if (wsUrl) return wsUrl;
    if (typeof window === 'undefined' || symbols.length === 0) return null;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const params = new URLSearchParams({ symbols: symbols.join(',') });
    return `${protocol}//${window.location.host}/ws/prices?${params.toString()}`;
  }, [symbols, wsUrl]);

  const handleMessage = useCallback((data: any) => {
    if (data.type === 'update' || data.type === 'snapshot') {
      setPrices(prev => ({
        ...prev,
        [data.symbol]: {
          symbol: data.symbol,
          price: data.price,
          change: data.change,
          change_pct: data.change_pct,
          volume: data.volume,
          timestamp: data.timestamp,
        },
      }));
      setFlashSymbol(data.symbol);
      setTimeout(() => setFlashSymbol(null), 500);
    }
  }, []);

  const { status } = useWebSocket(effectiveWsUrl, { onMessage: handleMessage });

  const statusColor = useMemo(() => {
    switch (status) {
      case 'connected': return 'success';
      case 'reconnecting': return 'warning';
      case 'disconnected': return 'error';
    }
  }, [status]);

  const statusLabel = useMemo(() => {
    switch (status) {
      case 'connected': return getMessage(locale, 'interaction.realtimeConnected');
      case 'reconnecting': return getMessage(locale, 'interaction.realtimeReconnecting');
      case 'disconnected': return getMessage(locale, 'interaction.realtimeDisconnected');
    }
  }, [status, locale]);

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <Chip label={statusLabel} color={statusColor as any} size="small" />
      </Stack>
      <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 1 }}>
        {symbols.map(symbol => {
          const data = prices[symbol];
          const isFlashing = flashSymbol === symbol;
          const isUp = data ? data.change_pct >= 0 : true;

          return (
            <Card
              key={symbol}
              sx={{
                minWidth: 140,
                transition: 'background-color 0.3s',
                backgroundColor: isFlashing
                  ? (isUp ? 'rgba(211, 47, 47, 0.05)' : 'rgba(46, 125, 50, 0.05)')
                  : undefined,
              }}
            >
              <CardContent sx={{ py: 1, px: 1.5, '&:last-child': { pb: 1 } }}>
                <Typography variant="caption" color="text.secondary">
                  {symbol}
                </Typography>
                <Typography
                  variant="body1"
                  fontWeight="bold"
                  color={isUp ? 'error.main' : 'success.main'}
                >
                  {data ? `$${data.price.toFixed(2)}` : '--'}
                </Typography>
                <Typography
                  variant="caption"
                  color={isUp ? 'error.main' : 'success.main'}
                >
                  {data ? `${isUp ? '+' : ''}${data.change_pct.toFixed(2)}%` : '--'}
                </Typography>
                {showVolume && data && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Vol: {(data.volume / 1_000_000).toFixed(1)}M
                  </Typography>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
}
