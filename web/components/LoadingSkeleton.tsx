'use client';

import { Box, Skeleton, Stack } from '@mui/material';

interface LoadingSkeletonProps {
  variant?: 'card' | 'table' | 'chart' | 'page';
  rows?: number;
}

export function LoadingSkeleton({ variant = 'page', rows = 5 }: LoadingSkeletonProps) {
  switch (variant) {
    case 'card':
      return (
        <Stack spacing={1} sx={{ p: 2 }} data-testid="loading-skeleton-card">
          <Skeleton variant="text" width="60%" height={32} />
          <Skeleton variant="rectangular" height={120} />
          <Skeleton variant="text" width="40%" />
        </Stack>
      );
    case 'table':
      return (
        <Stack spacing={1} sx={{ p: 2 }} data-testid="loading-skeleton-table">
          <Skeleton variant="rectangular" height={40} />
          {Array.from({ length: rows }).map((_, i) => (
            <Skeleton key={i} variant="rectangular" height={48} data-testid="loading-skeleton-row" />
          ))}
        </Stack>
      );
    case 'chart':
      return (
        <Box sx={{ p: 2 }} data-testid="loading-skeleton-chart">
          <Skeleton variant="text" width="30%" height={28} />
          <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 1 }} />
        </Box>
      );
    case 'page':
    default:
      return (
        <Stack spacing={2} sx={{ p: 3 }} data-testid="loading-skeleton-page">
          <Skeleton variant="text" width="40%" height={40} />
          <Skeleton variant="rectangular" height={200} />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Skeleton variant="rectangular" height={150} sx={{ flex: 1 }} />
            <Skeleton variant="rectangular" height={150} sx={{ flex: 1 }} />
          </Stack>
        </Stack>
      );
  }
}
