'use client';

import { useState } from 'react';
import { Button, CircularProgress } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { updateTracking } from '@/lib/api';
import { useLocale } from '@/components/LocaleProvider';
import { getMessage } from '@/i18n/get-message';

interface RefreshButtonProps {
  onRefreshed: () => void;
}

export default function RefreshButton({ onRefreshed }: RefreshButtonProps) {
  const { locale } = useLocale();
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await updateTracking();
      onRefreshed();
    } catch {
      // refresh failed silently, user can retry
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="outlined"
      size="small"
      startIcon={loading ? <CircularProgress size={16} /> : <RefreshIcon />}
      onClick={handleRefresh}
      disabled={loading}
      sx={{ borderRadius: '12px' }}
    >
      {getMessage(locale, 'interaction.trackingRefresh')}
    </Button>
  );
}