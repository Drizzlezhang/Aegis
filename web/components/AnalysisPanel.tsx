'use client';

import { LinearProgress, Paper, Stack, Typography } from '@mui/material';

interface VolumeProfile {
  poc: number;
  vah: number;
  val: number;
  volumeAtPoc: number;
}

interface GexWall {
  strike: number;
  gamma: number;
  type: 'call' | 'put';
  strength: string;
}

interface AnalysisPanelProps {
  volumeProfile: VolumeProfile;
  gexWalls: GexWall[];
}

export default function AnalysisPanel({ volumeProfile, gexWalls }: AnalysisPanelProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <VolumeProfileCard profile={volumeProfile} />
      <GexWallsCard walls={gexWalls} />
    </div>
  );
}

function VolumeProfileCard({ profile }: { profile: VolumeProfile }) {
  const { poc, vah, val, volumeAtPoc } = profile;
  const range = vah - val;
  const pocPct = range > 0 ? ((poc - val) / range) * 100 : 50;

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        Volume Profile
      </Typography>
      <Stack spacing={2}>
        <MetricRow label="POC" value={`$${poc.toFixed(2)}`} />
        <MetricRow label="VAH" value={`$${vah.toFixed(2)}`} />
        <MetricRow label="VAL" value={`$${val.toFixed(2)}`} />
        <MetricRow label="Vol@POC" value={volumeAtPoc.toLocaleString()} />

        <div className="mt-2">
          <div className="flex justify-between text-xs text-slate-500">
            <span>VAL ${val.toFixed(0)}</span>
            <span>VAH ${vah.toFixed(0)}</span>
          </div>
          <LinearProgress
            variant="determinate"
            value={pocPct}
            sx={{
              mt: 1,
              height: 10,
              borderRadius: 999,
              bgcolor: 'action.hover',
              '& .MuiLinearProgress-bar': {
                borderRadius: 999,
                backgroundColor: '#6750A4',
              },
            }}
          />
          <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center', color: 'text.secondary' }}>
            POC position
          </Typography>
        </div>
      </Stack>
    </Paper>
  );
}

function GexWallsCard({ walls }: { walls: GexWall[] }) {
  const maxGamma = Math.max(...walls.map((w) => w.gamma), 0.01);

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        GEX Walls
      </Typography>
      <Stack spacing={2}>
        {walls.map((w, i) => {
          const pct = (w.gamma / maxGamma) * 100;
          const color = w.type === 'call' ? '#10b981' : '#f43f5e';
          return (
            <Paper key={i} elevation={0} sx={{ p: 1.5, borderRadius: '18px', bgcolor: 'action.hover' }}>
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold text-[var(--foreground)]">
                  ${w.strike} {w.type.toUpperCase()}
                </span>
                <span className={`text-xs ${w.strength === 'strong' ? 'text-amber-500' : 'text-slate-500'}`}>
                  {w.strength}
                </span>
              </div>
              <LinearProgress
                variant="determinate"
                value={pct}
                sx={{
                  mt: 1,
                  height: 8,
                  borderRadius: 999,
                  bgcolor: 'action.selected',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 999,
                    backgroundColor: color,
                  },
                }}
              />
              <Typography variant="caption" sx={{ mt: 0.75, display: 'block', textAlign: 'right', color: 'text.secondary' }}>
                {w.gamma.toFixed(2)}
              </Typography>
            </Paper>
          );
        })}
      </Stack>
    </Paper>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
        {value}
      </Typography>
    </div>
  );
}
