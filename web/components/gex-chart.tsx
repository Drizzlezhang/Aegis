'use client';

import { Paper, Typography } from '@mui/material';
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

interface GexWall {
  strike: number;
  gamma: number;
  type: 'call' | 'put';
  strength: string;
}

interface GEXChartProps {
  walls: GexWall[];
  currentPrice: number;
}

export default function GEXChart({ walls, currentPrice }: GEXChartProps) {
  const callData = walls
    .filter((w) => w.type === 'call')
    .map((w) => ({
      x: w.strike,
      y: w.gamma,
      z: w.strength === 'strong' ? 300 : w.strength === 'moderate' ? 200 : 100,
      type: w.type,
      strength: w.strength,
    }));

  const putData = walls
    .filter((w) => w.type === 'put')
    .map((w) => ({
      x: w.strike,
      y: w.gamma,
      z: w.strength === 'strong' ? 300 : w.strength === 'moderate' ? 200 : 100,
      type: w.type,
      strength: w.strength,
    }));

  const maxGamma = Math.max(...walls.map((w) => w.gamma), 0.1);

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        GEX Walls
      </Typography>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,140,0.2)" />
          <XAxis
            type="number"
            dataKey="x"
            name="Strike"
            stroke="#7c7c8c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            domain={[
              Math.min(...walls.map((w) => w.strike), currentPrice) * 0.95,
              Math.max(...walls.map((w) => w.strike), currentPrice) * 1.05,
            ]}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Gamma"
            stroke="#7c7c8c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            domain={[0, maxGamma * 1.2]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            width={45}
          />
          <ZAxis type="number" dataKey="z" range={[50, 300]} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{
              backgroundColor: 'rgba(24,24,30,0.96)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '16px',
              fontSize: '12px',
            }}
            formatter={(_: unknown, __: unknown, props: { payload?: { x: number; y: number; type: string; strength: string } }) => {
              if (!props?.payload) return [];
              const p = props.payload;
              return [
                `Strike: $${p.x.toFixed(2)}\nGamma: ${(p.y * 100).toFixed(1)}%\nStrength: ${p.strength}`,
                p.type === 'call' ? 'Call Wall' : 'Put Wall',
              ];
            }}
            labelStyle={{ color: '#b0b0bb' }}
          />
          <ReferenceLine
            x={currentPrice}
            stroke="#6750A4"
            strokeDasharray="5 5"
            label={{
              value: `Spot $${currentPrice.toFixed(0)}`,
              position: 'insideTopRight',
              fill: '#6750A4',
              fontSize: 10,
            }}
          />
          <Scatter name="Call Walls" data={callData} fill="#f43f5e" opacity={0.8} />
          <Scatter name="Put Walls" data={putData} fill="#10b981" opacity={0.8} />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="mt-2 flex gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-rose-500" />
          Call Wall
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
          Put Wall
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[color:#6750A4]" />
          Spot Price
        </span>
      </div>
    </Paper>
  );
}
