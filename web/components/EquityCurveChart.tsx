'use client';

import { Box, Typography } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export interface EquityCurvePoint {
  date: string;
  equity: number;
  benchmark?: number;
}

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
}

export default function EquityCurveChart({ data }: EquityCurveChartProps) {
  if (!data || data.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 250,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No data
        </Typography>
      </Box>
    );
  }

  const hasBenchmark = data.some((d) => d.benchmark !== undefined);

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#1976d2"
          dot={false}
          strokeWidth={2}
          name="Portfolio"
        />
        {hasBenchmark && (
          <Line
            type="monotone"
            dataKey="benchmark"
            stroke="#9e9e9e"
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="5 5"
            name="Benchmark"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
