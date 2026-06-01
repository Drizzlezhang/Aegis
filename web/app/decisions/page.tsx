'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Chip, Paper,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';

interface DecisionItem {
  decision_id: string;
  symbol?: string;
  decision_type?: string;
  created_at?: string;
  fused_sentiment?: string;
  has_conflict?: boolean;
  [key: string]: unknown;
}

interface DecisionsResponse {
  items: DecisionItem[];
}

const SENTIMENT_COLORS: Record<string, 'success' | 'error' | 'default'> = {
  BULLISH: 'success',
  BEARISH: 'error',
  NEUTRAL: 'default',
};

const SENTIMENT_LABELS: Record<string, string> = {
  BULLISH: '看多',
  BEARISH: '看空',
  NEUTRAL: '中性',
};

export default function DecisionsPage() {
  const { locale } = useLocale();
  const router = useRouter();
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDecisions = useCallback(async () => {
    try {
      const res = await fetch('/api/decisions?limit=50');
      const data: DecisionsResponse = await res.json();
      setDecisions(data.items || []);
    } catch {
      // graceful degradation
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void fetchDecisions();
  }, [fetchDecisions]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      void fetchDecisions();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDecisions]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6">
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {getMessage(locale, 'common.decisions')}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
                决策记录列表，点击行查看详细 Trace
              </Typography>
            </div>

            {loading ? (
              <div className="card-muted text-center">
                <p className="text-slate-500">{getMessage(locale, 'common.loading')}</p>
              </div>
            ) : decisions.length === 0 ? (
              <div className="card-muted text-center">
                <p className="text-slate-500">暂无决策数据</p>
              </div>
            ) : (
              <TableContainer
                component={Paper}
                elevation={0}
                sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}
              >
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>时间</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell>融合情绪</TableCell>
                      <TableCell>冲突</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {decisions.map((d) => (
                      <TableRow
                        key={d.decision_id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => router.push(`/decisions/${d.decision_id}`)}
                      >
                        <TableCell sx={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                          {d.created_at ? new Date(d.created_at).toLocaleString() : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Chip label={d.symbol || 'N/A'} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Chip label={d.decision_type || 'N/A'} size="small" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={SENTIMENT_LABELS[d.fused_sentiment || ''] || d.fused_sentiment || 'N/A'}
                            size="small"
                            color={SENTIMENT_COLORS[d.fused_sentiment || ''] || 'default'}
                          />
                        </TableCell>
                        <TableCell>
                          {d.has_conflict ? (
                            <Chip label="冲突" size="small" color="warning" />
                          ) : (
                            <Chip label="一致" size="small" color="default" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
