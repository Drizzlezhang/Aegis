'use client';

import { Paper, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface VolumeProfileChartProps {
  poc: number;
  vah: number;
  val: number;
  volumeAtPoc: number;
  currentPrice: number;
}

export default function VolumeProfileChart({
  poc,
  vah,
  val,
  volumeAtPoc,
  currentPrice,
}: VolumeProfileChartProps) {
  const bins = 12;
  const range = vah - val;
  const binSize = range / bins;
  const data = [];

  for (let i = 0; i < bins; i++) {
    const priceLevel = val + binSize * i + binSize / 2;
    const distanceFromPoc = Math.abs(priceLevel - poc) / (range / 2);
    const volume = Math.round(volumeAtPoc * Math.max(0.2, 1 - distanceFromPoc * 0.9));
    data.push({
      level: `$${priceLevel.toFixed(0)}`,
      volume,
      rawPrice: priceLevel,
    });
  }

  const isInValueArea = (price: number) => price >= val && price <= vah;

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        Volume Profile
      </Typography>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,140,0.2)" horizontal={false} />
          <XAxis
            dataKey="level"
            stroke="#7c7c8c"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            interval={2}
          />
          <YAxis
            stroke="#7c7c8c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${(v / 1e6).toFixed(1)}M`}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(24,24,30,0.96)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '16px',
              fontSize: '12px',
            }}
            formatter={(value) => {
              const num = typeof value === 'number' ? value : Number(value);
              return [num.toLocaleString(), 'Volume'];
            }}
            labelStyle={{ color: '#b0b0bb' }}
          />
          <ReferenceLine
            x={`$${val.toFixed(0)}`}
            stroke="#f59e0b"
            strokeDasharray="3 3"
            label={{ value: 'VAL', position: 'insideTopRight', fill: '#f59e0b', fontSize: 10 }}
          />
          <ReferenceLine
            x={`$${poc.toFixed(0)}`}
            stroke="#6750A4"
            strokeWidth={2}
            label={{ value: 'POC', position: 'insideTopLeft', fill: '#6750A4', fontSize: 10 }}
          />
          <ReferenceLine
            x={`$${vah.toFixed(0)}`}
            stroke="#f59e0b"
            strokeDasharray="3 3"
            label={{ value: 'VAH', position: 'insideTopLeft', fill: '#f59e0b', fontSize: 10 }}
          />
          <Bar dataKey="volume" fill="#6750A4" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={isInValueArea(entry.rawPrice) ? '#6750A4' : '#7c7c8c'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>POC: <span className="text-[color:#6750A4]">${poc.toFixed(2)}</span></span>
        <span>VAH: <span className="text-amber-500">${vah.toFixed(2)}</span></span>
        <span>VAL: <span className="text-amber-500">${val.toFixed(2)}</span></span>
      </div>
    </Paper>
  );
}
