'use client';

import { Chip } from '@mui/material';

interface PhaseData {
  type: 'phase';
  symbol: string;
  phase: string;
  confidence: number;
  composite_score: number;
  transition: string | null;
  timestamp: string;
}

interface PhaseHistoryProps {
  history: PhaseData[];
}

export function PhaseHistory({ history }: PhaseHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">阶段历史</h2>
        <p className="text-sm text-slate-500">暂无历史数据</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold">阶段历史</h2>
      <div className="max-h-96 space-y-2 overflow-y-auto">
        {history.map((item, i) => (
          <div
            key={`${item.symbol}-${item.timestamp}-${i}`}
            className="flex items-center justify-between rounded-lg border border-[var(--outline)] p-3"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold">{item.symbol}</span>
              <Chip label={item.phase} size="small" color="primary" variant="outlined" />
              {item.transition && (
                <span className="text-xs text-amber-600">{item.transition}</span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>置信度 {(item.confidence * 100).toFixed(0)}%</span>
              <span>评分 {item.composite_score.toFixed(2)}</span>
              <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
