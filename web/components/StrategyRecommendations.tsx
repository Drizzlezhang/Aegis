'use client';

import { Chip, Paper, Stack, Typography } from '@mui/material';
import type { StrategyRecommendation } from '@/lib/api';

interface StrategyRecommendationsProps {
  recommendations: StrategyRecommendation[];
}

export default function StrategyRecommendations({ recommendations }: StrategyRecommendationsProps) {
  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        Strategy Recommendations
      </Typography>
      <Stack spacing={2}>
        {recommendations.map((rec) => (
          <Paper
            key={rec.id}
            elevation={0}
            className="card-muted"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Chip label={rec.type} size="small" color="primary" variant="outlined" />
                <RiskBadge level={rec.riskLevel} />
              </div>
              <Typography variant="body2" sx={{ fontWeight: 700, color: 'success.main' }}>
                {rec.expectedReturn}
              </Typography>
            </div>

            <Typography variant="body2" sx={{ mt: 1.5, color: 'text.primary' }}>
              {rec.description}
            </Typography>

            {(rec.expiration || rec.strike) && (
              <div className="mt-2 flex gap-3 text-xs text-slate-500">
                {rec.expiration && <span>Exp: {rec.expiration}</span>}
                {rec.strike && <span>Strike: {rec.strike}</span>}
              </div>
            )}
          </Paper>
        ))}
      </Stack>
    </Paper>
  );
}

function RiskBadge({ level }: { level: StrategyRecommendation['riskLevel'] }) {
  const colorMap: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    low: 'success',
    medium: 'warning',
    high: 'error',
  };

  return <Chip label={level} size="small" color={colorMap[level] || 'default'} />;
}
