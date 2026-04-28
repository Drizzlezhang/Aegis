'use client';

import { useEffect, useState } from 'react';
import { Button, Chip, Paper, Stack, TextField, Typography } from '@mui/material';
import {
  getMemoryStats,
  getMarketNotes,
  searchMemory,
  type MemoryStats,
  type MarketNoteItem,
  type MemorySearchResult,
} from '@/lib/api';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from './LocaleProvider';

export default function MemoryPageContent() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [notes, setNotes] = useState<MarketNoteItem[]>([]);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MemorySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const { locale } = useLocale();

  useEffect(() => {
    Promise.all([getMemoryStats(), getMarketNotes(undefined, undefined, 10)])
      .then(([s, n]) => {
        setStats(s);
        setNotes(n);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const resp = await searchMemory(query, undefined, 5);
      setSearchResults(resp.results);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="card">
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Aegis 记忆</h1>
        <p className="mt-1 text-sm text-slate-500">语义搜索与交易记忆</p>
      </div>

      {loading && (
        <Paper elevation={0} className="card">
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.loadingMemory')}
          </Typography>
        </Paper>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label={getMessage(locale, 'interaction.analysisResults')} value={stats.analysis_results} />
          <StatCard label={getMessage(locale, 'interaction.marketNotes')} value={stats.market_notes} />
          <StatCard label={getMessage(locale, 'interaction.tradingActions')} value={stats.trading_actions} />
          <StatCard label={getMessage(locale, 'interaction.embeddingDim')} value={stats.embedding_dimension} />
        </div>
      )}

      <Paper elevation={0} className="card">
        <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.semanticSearch')}
        </Typography>
        <div className="flex gap-2">
          <TextField
            fullWidth
            size="small"
            placeholder={getMessage(locale, 'interaction.searchAnalysisResults')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            variant="contained"
            sx={{ minWidth: 120, borderRadius: '16px', px: 2.5, fontWeight: 700 }}
          >
            {searching ? getMessage(locale, 'interaction.searching') : getMessage(locale, 'common.search')}
          </Button>
        </div>

        {searchResults.length > 0 && (
          <Stack spacing={2} sx={{ mt: 2 }}>
            {searchResults.map((r) => (
              <Paper key={r.id} elevation={0} className="card-muted">
                <div className="flex items-center justify-between gap-3">
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary' }}>
                    ID: {r.id}
                  </Typography>
                  <Chip label={`${(r.similarity_score * 100).toFixed(1)}% match`} size="small" color="success" variant="outlined" />
                </div>
                <Typography variant="body2" sx={{ mt: 1.5, color: 'text.secondary', lineHeight: 1.7 }}>
                  {r.document}
                </Typography>
              </Paper>
            ))}
          </Stack>
        )}

        {searchResults.length === 0 && !searching && query && (
          <Typography variant="caption" sx={{ mt: 2, display: 'block', color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.noResultsFound')}
          </Typography>
        )}
      </Paper>

      <Paper elevation={0} className="card">
        <div className="mb-3 flex items-center justify-between gap-3">
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {getMessage(locale, 'interaction.marketNotes')}
          </Typography>
          <Chip label={String(notes.length)} size="small" variant="outlined" />
        </div>
        {notes.length === 0 ? (
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.noMarketNotesYet')}
          </Typography>
        ) : (
          <Stack spacing={2}>
            {notes.map((note) => (
              <Paper key={note.id} elevation={0} className="card-muted">
                <div className="flex items-center justify-between gap-3">
                  <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                    {note.symbol || getMessage(locale, 'interaction.general')}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {note.note_date}
                  </Typography>
                </div>
                <Chip label={note.category} size="small" sx={{ mt: 1.5, width: 'fit-content' }} />
                <Typography variant="body2" sx={{ mt: 1.5, color: 'text.secondary', lineHeight: 1.7 }}>
                  {note.content}
                </Typography>
                {note.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {note.tags.map((tag) => (
                      <Chip key={tag} label={`#${tag}`} size="small" variant="outlined" />
                    ))}
                  </div>
                )}
              </Paper>
            ))}
          </Stack>
        )}
      </Paper>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Paper elevation={0} className="card-muted">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">{value}</p>
    </Paper>
  );
}
