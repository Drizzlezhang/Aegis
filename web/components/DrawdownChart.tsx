'use client';

import { Box, Typography } from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

interface DrawdownChartProps {
  data: DrawdownPoint[];
  maxDrawdown?: number;
}

export default function DrawdownChart({ data, maxDrawdown }: DrawdownChartProps) {
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

  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(2)}%`} />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#d32f2f"
          fill="#ffcdd2"
          dot={false}
        />
        {maxDrawdown !== undefined && (
          <ReferenceLine
            y={maxDrawdown}
            stroke="#d32f2f"
            strokeDasharray="3 3"
            label={{
              value: `Max: ${(maxDrawdown * 100).toFixed(1)}%`,
              position: 'insideBottomRight',
              fontSize: 11,
            }}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
