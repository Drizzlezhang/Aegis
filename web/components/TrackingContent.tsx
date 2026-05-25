'use client';

import { useState } from 'react';
import TrackingSummaryCards from '@/components/TrackingSummaryCards';
import TrackingStrategyTable from '@/components/TrackingStrategyTable';
import TrackingDecisionTable from '@/components/TrackingDecisionTable';
import RefreshButton from '@/components/RefreshButton';
import {
  getTrackingStats,
  getTrackedDecisions,
  type TrackingStats,
  type TrackedDecision,
} from '@/lib/api';
import { Stack, Typography } from '@mui/material';

interface TrackingContentProps {
  initialStats: TrackingStats | null;
  initialDecisions: TrackedDecision[] | null;
}

export default function TrackingContent({ initialStats, initialDecisions }: TrackingContentProps) {
  const [stats, setStats] = useState<TrackingStats | null>(initialStats);
  const [decisions, setDecisions] = useState<TrackedDecision[] | null>(initialDecisions);

  const handleRefresh = async () => {
    try {
      const newStats = await getTrackingStats();
      setStats(newStats);
    } catch {
      // keep current
    }
    try {
      const newDecisions = await getTrackedDecisions(20);
      setDecisions(newDecisions);
    } catch {
      // keep current
    }
  };

  return (
    <div className="mx-auto max-w-7xl">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Tracking
        </Typography>
        <RefreshButton onRefreshed={handleRefresh} />
      </Stack>
      <TrackingSummaryCards stats={stats} />
      <div className="mt-6">
        <TrackingStrategyTable stats={stats} />
      </div>
      <div className="mt-6">
        <TrackingDecisionTable decisions={decisions} />
      </div>
    </div>
  );
}