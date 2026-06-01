'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Box, Chip, FormControl, InputLabel, MenuItem, Paper, Select,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from '@/components/LocaleProvider';

interface SignalItem {
  id: string;
  source: string;
  signal_type: string;
  timestamp: string;
  symbols: string[];
  sentiment: string;
  confidence: number;
  title: string;
  content: string;
  raw_url: string;
}

interface SignalsResponse {
  items: SignalItem[];
  total: number;
  has_more: boolean;
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

export default function SignalsPage() {
  const { locale } = useLocale();
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('');
  const [sinceFilter, setSinceFilter] = useState<string>('');

  const fetchSignals = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (sourceFilter) params.set('source', sourceFilter);
      if (sentimentFilter) params.set('sentiment', sentimentFilter);
      if (sinceFilter) params.set('since', sinceFilter);
      params.set('limit', '50');

      const res = await fetch(`/api/signals?${params.toString()}`);
      const data: SignalsResponse = await res.json();
      setSignals(data.items);
    } catch {
      // graceful degradation
    }
    setLoading(false);
  }, [sourceFilter, sentimentFilter, sinceFilter]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      void fetchSignals();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6">
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {getMessage(locale, 'common.signals')}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
                {getMessage(locale, 'common.pushNotification')}
              </Typography>
            </div>

            {/* Filters */}
            <Paper
              elevation={0}
              sx={{
                p: 2,
                mb: 3,
                borderRadius: '16px',
                border: '1px solid',
                borderColor: 'divider',
                display: 'flex',
                gap: 2,
                flexWrap: 'wrap',
              }}
            >
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Source</InputLabel>
                <Select
                  value={sourceFilter}
                  label="Source"
                  onChange={(e) => setSourceFilter(e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="polymarket">Polymarket</MenuItem>
                  <MenuItem value="x_social">X Social</MenuItem>
                  <MenuItem value="macro_news">Macro News</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Sentiment</InputLabel>
                <Select
                  value={sentimentFilter}
                  label="Sentiment"
                  onChange={(e) => setSentimentFilter(e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="BULLISH">Bullish</MenuItem>
                  <MenuItem value="BEARISH">Bearish</MenuItem>
                  <MenuItem value="NEUTRAL">Neutral</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary' }}>
                  Since
                </Typography>
                <input
                  type="datetime-local"
                  value={sinceFilter}
                  onChange={(e) => setSinceFilter(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--mui-palette-divider)',
                    background: 'transparent',
                    color: 'inherit',
                    fontSize: '14px',
                  }}
                />
              </FormControl>
            </Paper>

            {/* Table */}
            {loading ? (
              <div className="card-muted text-center">
                <p className="text-slate-500">{getMessage(locale, 'common.loading')}</p>
              </div>
            ) : signals.length === 0 ? (
              <div className="card-muted text-center">
                <p className="text-slate-500">暂无信号数据</p>
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
                      <TableCell>来源</TableCell>
                      <TableCell>情绪</TableCell>
                      <TableCell>置信度</TableCell>
                      <TableCell>关联 Symbol</TableCell>
                      <TableCell>标题</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {signals.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell sx={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                          {new Date(s.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Chip label={s.source} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={SENTIMENT_LABELS[s.sentiment] || s.sentiment}
                            size="small"
                            color={SENTIMENT_COLORS[s.sentiment] || 'default'}
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box
                              sx={{
                                width: 40,
                                height: 6,
                                borderRadius: 3,
                                bgcolor: 'action.hover',
                                overflow: 'hidden',
                              }}
                            >
                              <Box
                                sx={{
                                  width: `${Math.round(s.confidence * 100)}%`,
                                  height: '100%',
                                  borderRadius: 3,
                                  bgcolor:
                                    s.confidence >= 0.7
                                      ? 'success.main'
                                      : s.confidence >= 0.4
                                        ? 'warning.main'
                                        : 'error.main',
                                }}
                              />
                            </Box>
                            <Typography variant="body2">
                              {Math.round(s.confidence * 100)}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          {s.symbols.map((sym) => (
                            <Chip key={sym} label={sym} size="small" sx={{ mr: 0.5 }} />
                          ))}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.raw_url ? (
                            <a href={s.raw_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                              {s.title}
                            </a>
                          ) : (
                            s.title
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
