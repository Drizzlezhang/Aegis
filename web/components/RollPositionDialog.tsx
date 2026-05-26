'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';
import type { PositionItem, RollPositionPayload } from '@/lib/api';

interface RollPositionDialogProps {
  open: boolean;
  position: PositionItem | null;
  onClose: () => void;
  onConfirm: (positionId: string, payload: RollPositionPayload) => Promise<void>;
}

export default function RollPositionDialog({ open, position, onClose, onConfirm }: RollPositionDialogProps) {
  const [newStrike, setNewStrike] = useState('');
  const [newExpiry, setNewExpiry] = useState('');
  const [newEntryPrice, setNewEntryPrice] = useState('');
  const [newQuantity, setNewQuantity] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (position) {
      setNewStrike('');
      setNewExpiry('');
      setNewEntryPrice('');
      setNewQuantity('');
    }
  }, [position]);

  const handleConfirm = useCallback(async () => {
    if (!position || !newStrike || !newExpiry || !newEntryPrice) return;
    setLoading(true);
    try {
      await onConfirm(position.id, {
        newStrike: parseFloat(newStrike),
        newExpiry,
        newEntryPrice: parseFloat(newEntryPrice),
        newQuantity: newQuantity ? parseInt(newQuantity, 10) : undefined,
      });
      onClose();
    } finally {
      setLoading(false);
    }
  }, [position, newStrike, newExpiry, newEntryPrice, newQuantity, onConfirm, onClose]);

  if (!position) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Roll Position — {position.symbol}</DialogTitle>
      <DialogContent>
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <Typography variant="caption" color="text.secondary">Current Strike</Typography>
            <Typography variant="body2" fontWeight={700}>${position.strike.toFixed(2)}</Typography>
          </div>
          <div>
            <Typography variant="caption" color="text.secondary">Current Expiry</Typography>
            <Typography variant="body2" fontWeight={700}>{position.expiry}</Typography>
          </div>
        </div>

        <TextField
          label="New Strike"
          type="number"
          fullWidth
          value={newStrike}
          onChange={(e) => setNewStrike(e.target.value)}
          sx={{ mb: 2 }}
          inputProps={{ step: 0.01 }}
        />

        <TextField
          label="New Expiry (YYYY-MM-DD)"
          fullWidth
          value={newExpiry}
          onChange={(e) => setNewExpiry(e.target.value)}
          sx={{ mb: 2 }}
          placeholder="2026-12-31"
        />

        <TextField
          label="New Entry Price"
          type="number"
          fullWidth
          value={newEntryPrice}
          onChange={(e) => setNewEntryPrice(e.target.value)}
          sx={{ mb: 2 }}
          inputProps={{ step: 0.01 }}
        />

        <TextField
          label="New Quantity (optional, default: same)"
          type="number"
          fullWidth
          value={newQuantity}
          onChange={(e) => setNewQuantity(e.target.value)}
          inputProps={{ min: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>Cancel</Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color="primary"
          disabled={loading || !newStrike || !newExpiry || !newEntryPrice}
        >
          {loading ? 'Rolling...' : 'Confirm Roll'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
