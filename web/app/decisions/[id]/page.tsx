'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, notFound } from 'next/navigation';
import {
  Box, Chip, Paper, Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';

interface SignalItem {
  id?: string;
  source?: string;
  signal_type?: string;
  timestamp?: string;
  symbols?: string[];
  sentiment?: string;
  confidence?: number;
  title?: string;
  content?: string;
  raw_url?: string;
  [key: string]: unknown;
}

interface FusionData {
  overall_sentiment?: string;
  fusion_confidence?: number;
  bullish_count?: number;
  bearish_count?: number;
  neutral_count?: number;
  has_conflict?: boolean;
  conflict_axis?: string | null;
  conflict_explanation?: string | null;
  watch_point?: string | null;
  [key: string]: unknown;
}

interface WyckoffAndFinal {
  wyckoff_phase?: string;
  action?: string;
  rationale?: string;
  current_price?: number;
  [key: string]: unknown;
}

interface DecisionTrace {
  decision_id: string;
  signals: SignalItem[];
  fusion: FusionData;
  wyckoff_and_final: WyckoffAndFinal;
}

const SENTIMENT_COLORS: Record<string, 'success' | 'error' | 'default'> = {
  BULLISH: 'success',
  BEARISH: 'error',
  NEUTRAL: 'default',
};

export default function DecisionTracePage() {
  const { locale } = useLocale();
  const params = useParams();
  const id = params?.id as string;
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    void (async () => {
      try {
        const res = await fetch(`/api/decisions/${id}/trace`);
        if (!res.ok) {
          setError(true);
          return;
        }
        const data: DecisionTrace = await res.json();
        setTrace(data);
      } catch {
        setError(true);
      }
      setLoading(false);
    })();
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-4 lg:p-6">
            <div className="card-muted text-center">
              <p className="text-slate-500">{getMessage(locale, 'common.loading')}</p>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (error || !trace) {
    notFound();
  }

  const { signals, fusion, wyckoff_and_final } = trace;
  const hasConflict = fusion?.has_conflict === true;

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Link href="/decisions" className="hover:text-slate-300">
                {getMessage(locale, 'common.decisions')}
              </Link>
              <span>/</span>
              <span className="text-slate-300">{id}</span>
            </div>

            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              Decision Trace
            </Typography>

            {/* Section 1: Signal Events */}
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: '16px',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                段 1: 信号事件 ({signals?.length ?? 0})
              </Typography>
              <div className="space-y-3">
                {signals && signals.length > 0 ? (
                  signals.map((s, idx) => (
                    <Paper
                      key={s.id || idx}
                      elevation={0}
                      sx={{
                        p: 2,
                        borderRadius: '12px',
                        border: '1px solid',
                        borderColor: 'divider',
                        bgcolor: 'action.hover',
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Chip label={(s.source as string) || 'unknown'} size="small" variant="outlined" />
                          <Chip
                            label={(s.sentiment as string) || 'N/A'}
                            size="small"
                            color={SENTIMENT_COLORS[s.sentiment as string] || 'default'}
                          />
                        </div>
                        {s.confidence != null && (
                          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                            {Math.round((s.confidence as number) * 100)}% confidence
                          </Typography>
                        )}
                      </div>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {(s.title as string) || 'Untitled'}
                      </Typography>
                      {s.content && (
                        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
                          {s.content as string}
                        </Typography>
                      )}
                      {s.symbols && Array.isArray(s.symbols) && (
                        <div className="flex items-center gap-1 mt-2">
                          {s.symbols.map((sym: string) => (
                            <Chip key={sym} label={sym} size="small" />
                          ))}
                        </div>
                      )}
                    </Paper>
                  ))
                ) : (
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    暂无信号数据
                  </Typography>
                )}
              </div>
            </Paper>

            {/* Section 2: Fusion Conclusion */}
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: '16px',
                border: '1px solid',
                borderColor: hasConflict ? 'warning.main' : 'divider',
                bgcolor: hasConflict ? 'warning.dark' : undefined,
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                段 2: 融合结论
              </Typography>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                <div className="text-center">
                  <Typography variant="h5" sx={{ fontWeight: 700, color: 'success.main' }}>
                    {fusion?.bullish_count ?? 0}
                  </Typography>
                  <Typography variant="caption">看多</Typography>
                </div>
                <div className="text-center">
                  <Typography variant="h5" sx={{ fontWeight: 700, color: 'error.main' }}>
                    {fusion?.bearish_count ?? 0}
                  </Typography>
                  <Typography variant="caption">看空</Typography>
                </div>
                <div className="text-center">
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {fusion?.neutral_count ?? 0}
                  </Typography>
                  <Typography variant="caption">中性</Typography>
                </div>
                <div className="text-center">
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {fusion?.fusion_confidence != null ? `${Math.round(fusion.fusion_confidence * 100)}%` : 'N/A'}
                  </Typography>
                  <Typography variant="caption">融合置信度</Typography>
                </div>
              </div>
              <Chip
                label={(fusion?.overall_sentiment as string) || 'N/A'}
                color={SENTIMENT_COLORS[fusion?.overall_sentiment as string] || 'default'}
                size="small"
              />

              {hasConflict && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    borderRadius: '12px',
                    border: '1px solid',
                    borderColor: 'warning.main',
                    bgcolor: 'rgba(255,152,0,0.1)',
                  }}
                >
                  <Typography variant="subtitle2" sx={{ color: 'warning.main', fontWeight: 700 }}>
                    ⚠ 冲突检测: {(fusion?.conflict_axis as string) || 'Unknown'}
                  </Typography>
                  {fusion?.conflict_explanation && (
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      {fusion.conflict_explanation as string}
                    </Typography>
                  )}
                  {fusion?.watch_point && (
                    <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 600 }}>
                      关注点: {fusion.watch_point as string}
                    </Typography>
                  )}
                </Box>
              )}
            </Paper>

            {/* Section 3: Wyckoff + Final Action */}
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: '16px',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                段 3: Wyckoff 阶段 & 最终决策
              </Typography>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Wyckoff Phase
                  </Typography>
                  <Chip
                    label={(wyckoff_and_final?.wyckoff_phase as string) || 'N/A'}
                    color="primary"
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </div>
                <div>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Action
                  </Typography>
                  <Chip
                    label={(wyckoff_and_final?.action as string) || 'N/A'}
                    color="secondary"
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </div>
              </div>
              <Box sx={{ mt: 3, p: 2, borderRadius: '12px', bgcolor: 'action.hover' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  最终决策
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {wyckoff_and_final?.rationale
                    ? (wyckoff_and_final.rationale as string)
                    : `基于 ${fusion?.bullish_count ?? 0} 看多 / ${fusion?.bearish_count ?? 0} 看空信号，整体情绪: ${fusion?.overall_sentiment || 'N/A'}`}
                </Typography>
              </Box>
            </Paper>
          </div>
        </main>
      </div>
    </div>
  );
}
