'use client';

import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface PriceChartProps {
  currentPrice: number;
  supports: { level: number; strength: string }[];
  resistances: { level: number; strength: string }[];
}

export default function PriceChart({
  currentPrice,
  supports,
  resistances,
}: PriceChartProps) {
  const data = useMemo(() => {
    // Generate 30 days of mock price data based on current price
    const days = 30;
    const volatility = currentPrice * 0.02;
    const result = [];
    let price = currentPrice * (1 - (Math.random() * 0.06 - 0.03));

    for (let i = 0; i < days; i++) {
      const change = (Math.random() - 0.48) * volatility;
      price += change;
      const date = new Date();
      date.setDate(date.getDate() - (days - 1 - i));
      result.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        price: Math.max(price, currentPrice * 0.85),
        fullDate: date.toISOString(),
      });
    }
    // Ensure last point matches current price
    result[result.length - 1].price = currentPrice;
    return result;
  }, [currentPrice]);

  const minPrice = useMemo(
    () => Math.min(...data.map((d) => d.price), ...supports.map((s) => s.level)) * 0.98,
    [data, supports]
  );
  const maxPrice = useMemo(
    () => Math.max(...data.map((d) => d.price), ...resistances.map((r) => r.level)) * 1.02,
    [data, resistances]
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h3 className="mb-4 text-sm font-semibold text-slate-300">Price Trend (30D)</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            stroke="#475569"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            interval={4}
          />
          <YAxis
            domain={[minPrice, maxPrice]}
            stroke="#475569"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
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
              return [`$${num.toFixed(2)}`, 'Price'];
            }}
            labelStyle={{ color: '#94a3b8' }}
          />
          {/* Support lines */}
          {supports.slice(0, 2).map((s, i) => (
            <ReferenceLine
              key={`support-${i}`}
              y={s.level}
              stroke="#10b981"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `S${i + 1} $${s.level.toFixed(0)}`,
                position: 'insideTopRight',
                fill: '#10b981',
                fontSize: 10,
              }}
            />
          ))}
          {/* Resistance lines */}
          {resistances.slice(0, 2).map((r, i) => (
            <ReferenceLine
              key={`resistance-${i}`}
              y={r.level}
              stroke="#f43f5e"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `R${i + 1} $${r.level.toFixed(0)}`,
                position: 'insideBottomRight',
                fill: '#f43f5e',
                fontSize: 10,
              }}
            />
          ))}
          <Area
            type="monotone"
            dataKey="price"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#priceGradient)"
            dot={false}
            activeDot={{ r: 4, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
