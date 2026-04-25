'use client';

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
  // Generate mock volume distribution around POC
  const bins = 12;
  const range = vah - val;
  const binSize = range / bins;
  const data = [];

  for (let i = 0; i < bins; i++) {
    const priceLevel = val + binSize * i + binSize / 2;
    // Volume peaks at POC, tapers off
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
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h3 className="mb-4 text-sm font-semibold text-slate-300">Volume Profile</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis
            dataKey="level"
            stroke="#475569"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            interval={2}
          />
          <YAxis
            stroke="#475569"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${(v / 1e6).toFixed(1)}M`}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => {
              const num = typeof value === 'number' ? value : Number(value);
              return [num.toLocaleString(), 'Volume'];
            }}
            labelStyle={{ color: '#94a3b8' }}
          />
          {/* VAL line */}
          <ReferenceLine
            x={`$${val.toFixed(0)}`}
            stroke="#f59e0b"
            strokeDasharray="3 3"
            label={{ value: 'VAL', position: 'insideTopRight', fill: '#f59e0b', fontSize: 10 }}
          />
          {/* POC line */}
          <ReferenceLine
            x={`$${poc.toFixed(0)}`}
            stroke="#8b5cf6"
            strokeWidth={2}
            label={{ value: 'POC', position: 'insideTopLeft', fill: '#8b5cf6', fontSize: 10 }}
          />
          {/* VAH line */}
          <ReferenceLine
            x={`$${vah.toFixed(0)}`}
            stroke="#f59e0b"
            strokeDasharray="3 3"
            label={{ value: 'VAH', position: 'insideTopLeft', fill: '#f59e0b', fontSize: 10 }}
          />
          <Bar dataKey="volume" fill="#6366f1" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={isInValueArea(entry.rawPrice) ? '#6366f1' : '#334155'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>POC: <span className="text-violet-400">${poc.toFixed(2)}</span></span>
        <span>VAH: <span className="text-amber-400">${vah.toFixed(2)}</span></span>
        <span>VAL: <span className="text-amber-400">${val.toFixed(2)}</span></span>
      </div>
    </div>
  );
}
