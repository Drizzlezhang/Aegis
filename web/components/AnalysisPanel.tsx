'use client';

import type { VolumeProfile, GexWall } from '@/lib/mock-data';

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
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-slate-300">Volume Profile</h3>
      <div className="space-y-3">
        <MetricRow label="POC" value={`$${poc.toFixed(2)}`} />
        <MetricRow label="VAH" value={`$${vah.toFixed(2)}`} />
        <MetricRow label="VAL" value={`$${val.toFixed(2)}`} />
        <MetricRow label="Vol@POC" value={volumeAtPoc.toLocaleString()} />

        <div className="mt-2">
          <div className="flex justify-between text-xs text-slate-500">
            <span>VAL ${val.toFixed(0)}</span>
            <span>VAH ${vah.toFixed(0)}</span>
          </div>
          <div className="mt-1 h-2 w-full rounded-full bg-slate-800">
            <div
              className="h-2 rounded-full bg-blue-500"
              style={{ width: `${pocPct}%` }}
            />
          </div>
          <p className="mt-1 text-center text-xs text-slate-500">POC position</p>
        </div>
      </div>
    </div>
  );
}

function GexWallsCard({ walls }: { walls: GexWall[] }) {
  const maxGamma = Math.max(...walls.map((w) => w.gamma), 0.01);

  return (
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-slate-300">GEX Walls</h3>
      <div className="space-y-2">
        {walls.map((w, i) => {
          const pct = (w.gamma / maxGamma) * 100;
          const color = w.type === 'call' ? 'bg-emerald-500' : 'bg-rose-500';
          return (
            <div key={i} className="rounded-lg bg-slate-800/50 p-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-200">
                  ${w.strike} {w.type.toUpperCase()}
                </span>
                <span className={`text-xs ${w.strength === 'strong' ? 'text-amber-400' : 'text-slate-500'}`}>
                  {w.strength}
                </span>
              </div>
              <div className="mt-1 h-1.5 w-full rounded-full bg-slate-800">
                <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-0.5 text-right text-xs text-slate-500">{w.gamma.toFixed(2)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-200">{value}</span>
    </div>
  );
}
