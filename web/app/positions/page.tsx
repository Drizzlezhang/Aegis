'use client';

import { useCallback, useEffect, useState } from 'react';
import { Alert, Snackbar } from '@mui/material';
import AlertsPanel from '@/components/AlertsPanel';
import ClosePositionDialog from '@/components/ClosePositionDialog';
import Header from '@/components/Header';
import PipelineHealth from '@/components/PipelineHealth';
import PositionTable from '@/components/PositionTable';
import RollPositionDialog from '@/components/RollPositionDialog';
import Sidebar from '@/components/Sidebar';
import { usePositions } from '@/hooks/usePositions';
import { getStatus, getSymbols, type PipelineMetrics, type SymbolInfo } from '@/lib/api';
import type { ClosePositionPayload, PositionData, RollPositionPayload } from '@/lib/api';

export default function PositionsPage() {
  const { summary, positions, loading, error, handleClose, handleRoll } = usePositions();

  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [pipeline, setPipeline] = useState<PipelineMetrics | null>(null);

  const [closeTarget, setCloseTarget] = useState<PositionData | null>(null);
  const [rollTarget, setRollTarget] = useState<PositionData | null>(null);

  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  useEffect(() => {
    void getSymbols().then(setSymbols).catch(() => setSymbols([]));
    void getStatus().then((s) => setPipeline(s.pipeline)).catch(() => setPipeline(null));
  }, []);

  const showSnackbar = useCallback((message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity });
  }, []);

  const handleSnackbarClose = useCallback(() => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  }, []);

  const onClosePosition = useCallback(async (positionId: string, payload: ClosePositionPayload) => {
    await handleClose(positionId, payload);
    showSnackbar('Position closed successfully', 'success');
  }, [handleClose, showSnackbar]);

  const onRollPosition = useCallback(async (positionId: string, payload: RollPositionPayload) => {
    await handleRoll(positionId, payload);
    showSnackbar('Position rolled successfully', 'success');
  }, [handleRoll, showSnackbar]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-6xl space-y-4">
            <PositionTable
              positions={summary?.positions ?? []}
              summary={summary}
              onClose={setCloseTarget}
              onRoll={setRollTarget}
            />
            <AlertsPanel />
            <PipelineHealth pipeline={pipeline} />
          </div>
        </main>
      </div>

      <ClosePositionDialog
        open={closeTarget !== null}
        position={closeTarget ? {
          id: closeTarget.id,
          symbol: closeTarget.symbol,
          status: closeTarget.status,
          strike: closeTarget.strike,
          expiry: closeTarget.expiry,
          dte: closeTarget.dte,
          entryPrice: closeTarget.entry_price,
          currentPrice: closeTarget.current_price,
          pnl: closeTarget.pnl,
          pnlPct: closeTarget.pnl_pct,
          quantity: closeTarget.quantity,
        } : null}
        onClose={() => setCloseTarget(null)}
        onConfirm={onClosePosition}
      />

      <RollPositionDialog
        open={rollTarget !== null}
        position={rollTarget ? {
          id: rollTarget.id,
          symbol: rollTarget.symbol,
          status: rollTarget.status,
          strike: rollTarget.strike,
          expiry: rollTarget.expiry,
          dte: rollTarget.dte,
          entryPrice: rollTarget.entry_price,
          currentPrice: rollTarget.current_price,
          pnl: rollTarget.pnl,
          pnlPct: rollTarget.pnl_pct,
          quantity: rollTarget.quantity,
        } : null}
        onClose={() => setRollTarget(null)}
        onConfirm={onRollPosition}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleSnackbarClose} severity={snackbar.severity} variant="filled" sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
}
