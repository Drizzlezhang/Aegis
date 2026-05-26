'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  closePosition,
  type ClosePositionPayload,
  getPositionSummary,
  type PositionItem,
  type PositionSummaryData,
  rollPosition,
  type RollPositionPayload,
} from '@/lib/api';

interface UsePositionsReturn {
  summary: PositionSummaryData | null;
  positions: PositionItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  handleClose: (positionId: string, payload: ClosePositionPayload) => Promise<void>;
  handleRoll: (positionId: string, payload: RollPositionPayload) => Promise<void>;
}

export function usePositions(): UsePositionsReturn {
  const [summary, setSummary] = useState<PositionSummaryData | null>(null);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getPositionSummary();
      setSummary(data);
      setPositions(
        data.positions.map((p) => ({
          id: p.id,
          symbol: p.symbol,
          status: p.status,
          strike: p.strike,
          expiry: p.expiry,
          dte: p.dte,
          entryPrice: p.entry_price,
          currentPrice: p.current_price,
          pnl: p.pnl,
          pnlPct: p.pnl_pct,
          quantity: p.quantity,
        })),
      );
    } catch {
      // keep existing data on refresh failure
    }
  }, []);

  useEffect(() => {
    void refresh().finally(() => setLoading(false));
    const timer = setInterval(() => {
      void refresh();
    }, 30000);
    return () => {
      clearInterval(timer);
    };
  }, [refresh]);

  const showError = useCallback((msg: string) => {
    setError(msg);
    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
    }
    errorTimerRef.current = setTimeout(() => {
      setError(null);
    }, 3000);
  }, []);

  const handleClose = useCallback(
    async (positionId: string, payload: ClosePositionPayload) => {
      try {
        await closePosition(positionId, payload);
        await refresh();
      } catch (err) {
        showError(err instanceof Error ? err.message : 'Failed to close position');
      }
    },
    [refresh, showError],
  );

  const handleRoll = useCallback(
    async (positionId: string, payload: RollPositionPayload) => {
      try {
        await rollPosition(positionId, payload);
        await refresh();
      } catch (err) {
        showError(err instanceof Error ? err.message : 'Failed to roll position');
      }
    },
    [refresh, showError],
  );

  return { summary, positions, loading, error, refresh, handleClose, handleRoll };
}
