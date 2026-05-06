'use client';

import { Chip, LinearProgress, Paper, Stack, Typography } from '@mui/material';

interface SR {
  level: number;
  type: 'support' | 'resistance';
  strength: 'weak' | 'moderate' | 'strong';
  source: string;
}

interface SupportResistanceProps {
  supports: SR[];
  resistances: SR[];
  currentPrice: number;
}

export default function SupportResistance({ supports, resistances, currentPrice }: SupportResistanceProps) {
  const all = [
    ...supports.map((s) => ({ ...s, dist: ((currentPrice - s.level) / currentPrice) * 100 })),
    ...resistances.map((r) => ({ ...r, dist: ((r.level - currentPrice) / currentPrice) * 100 })),
  ].sort((a, b) => a.level - b.level);

  const minL = all[0]?.level ?? currentPrice * 0.8;
  const maxL = all[all.length - 1]?.level ?? currentPrice * 1.2;
  const range = maxL - minL || 1;

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        Support / Resistance
      </Typography>
      <Stack spacing={2}>
        {all.map((item, i) => {
          const pct = ((item.level - minL) / range) * 100;
          const isSupport = item.type === 'support';
          const barColor = isSupport ? '#10b981' : '#f43f5e';
          return (
            <div key={i} className="relative">
              <div className="flex items-center justify-between gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className={`inline-block h-2 w-2 rounded-full ${isSupport ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  <span className="font-medium text-[var(--foreground)]">${item.level.toFixed(2)}</span>
                  <span className={`text-xs ${isSupport ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {isSupport ? 'S' : 'R'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>{item.source}</Typography>
                  <StrengthBadge strength={item.strength} />
                  <Typography variant="caption" sx={{ minWidth: 42, textAlign: 'right', color: 'text.secondary' }}>
                    {item.dist.toFixed(1)}%
                  </Typography>
                </div>
              </div>
              <LinearProgress
                variant="determinate"
                value={pct}
                sx={{
                  mt: 1,
                  height: 6,
                  borderRadius: 999,
                  bgcolor: 'action.hover',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 999,
                    backgroundColor: barColor,
                  },
                }}
              />
            </div>
          );
        })}
      </Stack>

      <Paper elevation={0} className="card-muted" sx={{ mt: 2, textAlign: 'center' }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Current: <span className="font-semibold text-[var(--foreground)]">${currentPrice.toFixed(2)}</span>
        </Typography>
      </Paper>
    </Paper>
  );
}

function StrengthBadge({ strength }: { strength: SR['strength'] }) {
  const colorMap: Record<string, 'primary' | 'warning' | 'success'> = {
    weak: 'primary',
    moderate: 'warning',
    strong: 'success',
  };

  return <Chip label={strength} size="small" color={colorMap[strength] || 'primary'} variant="outlined" />;
}
