'use client';

import { Chip } from '@mui/material';
import type { WebSocketStatus } from '@/hooks/useWebSocket';

interface PhaseData {
  type: 'phase';
  symbol: string;
  phase: string;
  confidence: number;
  composite_score: number;
  transition: string | null;
  timestamp: string;
}

interface PhaseCurrentCardProps {
  phase: PhaseData | null;
  status: WebSocketStatus;
  symbol: string;
}

const statusLabel: Record<WebSocketStatus, string> = {
  connecting: '连接中...',
  connected: '已连接',
  reconnecting: '重连中...',
  disconnected: '未连接',
};

const statusColor: Record<WebSocketStatus, 'warning' | 'success' | 'error' | 'default'> = {
  connecting: 'warning',
  connected: 'success',
  reconnecting: 'warning',
  disconnected: 'default',
};

export function PhaseCurrentCard({ phase, status, symbol }: PhaseCurrentCardProps) {
  if (!symbol) {
    return (
      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">当前阶段</h2>
        <p className="text-sm text-slate-500">请选择一个标的以查看实时阶段数据</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">当前阶段 — {symbol}</h2>
        <Chip label={statusLabel[status]} size="small" color={statusColor[status]} />
      </div>

      {phase ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-bold text-blue-700 dark:bg-blue-900 dark:text-blue-200">
              {phase.phase}
            </span>
            {phase.transition && (
              <span className="text-xs text-slate-500">
                过渡: {phase.transition}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-slate-500">置信度</span>
              <div className="text-lg font-bold">{(phase.confidence * 100).toFixed(1)}%</div>
            </div>
            <div>
              <span className="text-slate-500">综合评分</span>
              <div className="text-lg font-bold">{phase.composite_score.toFixed(2)}</div>
            </div>
          </div>
          <div className="text-xs text-slate-400">
            更新于 {new Date(phase.timestamp).toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">等待阶段数据...</p>
      )}
    </div>
  );
}
