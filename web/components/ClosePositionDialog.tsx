'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import type { ClosePositionPayload, PositionItem } from '@/lib/api';

interface ClosePositionDialogProps {
  open: boolean;
  position: PositionItem | null;
  onClose: () => void;
  onConfirm: (positionId: string, payload: ClosePositionPayload) => Promise<void>;
}

const REASON_OPTIONS = [
  { value: 'target_hit', label: 'Target Hit' },
  { value: 'stop_loss', label: 'Stop Loss' },
  { value: 'manual', label: 'Manual' },
  { value: 'expiry', label: 'Expiry' },
];

export default function ClosePositionDialog({ open, position, onClose, onConfirm }: ClosePositionDialogProps) {
  const [closePrice, setClosePrice] = useState('');
  const [reason, setReason] = useState('manual');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (position) {
      setClosePrice(position.currentPrice?.toString() ?? '');
      setReason('manual');
    }
  }, [position]);

  const estimatedPnl = useMemo(() => {
    if (!position || !closePrice) return null;
    const price = parseFloat(closePrice);
    if (isNaN(price)) return null;
    return (price - position.entryPrice) * position.quantity * 100;
  }, [position, closePrice]);

  const handleConfirm = useCallback(async () => {
    if (!position || !closePrice) return;
    setLoading(true);
    try {
      await onConfirm(position.id, {
        closePrice: parseFloat(closePrice),
        reason,
      });
      onClose();
    } finally {
      setLoading(false);
    }
  }, [position, closePrice, reason, onConfirm, onClose]);

  if (!position) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Close Position — {position.symbol}</DialogTitle>
      <DialogContent>
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <Typography variant="caption" color="text.secondary">Entry Price</Typography>
            <Typography variant="body2" fontWeight={700}>${position.entryPrice.toFixed(2)}</Typography>
          </div>
          <div>
            <Typography variant="caption" color="text.secondary">Current Price</Typography>
            <Typography variant="body2" fontWeight={700}>
              {position.currentPrice != null ? `$${position.currentPrice.toFixed(2)}` : '--'}
            </Typography>
          </div>
        </div>

        <TextField
          label="Close Price"
          type="number"
          fullWidth
          value={closePrice}
          onChange={(e) => setClosePrice(e.target.value)}
          sx={{ mb: 2 }}
          inputProps={{ step: 0.01 }}
        />

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Reason</InputLabel>
          <Select value={reason} label="Reason" onChange={(e) => setReason(e.target.value)}>
            {REASON_OPTIONS.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {estimatedPnl !== null && (
          <Typography
            variant="body2"
            fontWeight={700}
            color={estimatedPnl >= 0 ? 'success.main' : 'error.main'}
          >
            Estimated P&L: {estimatedPnl >= 0 ? '+' : ''}${estimatedPnl.toFixed(2)}
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" color="error" disabled={loading || !closePrice}>
          {loading ? 'Closing...' : 'Confirm Close'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
