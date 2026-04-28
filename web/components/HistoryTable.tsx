'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Chip, Paper, Stack, TextField, Typography } from '@mui/material';
import { getAnalysisHistory, type HistoryEntry } from '@/lib/api';

export default function HistoryTable() {
  const router = useRouter();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    getAnalysisHistory(undefined, 50)
      .then((data) => {
        setEntries(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = filter
    ? entries.filter((e) => e.symbol.toLowerCase().includes(filter.toLowerCase()))
    : entries;

  if (loading) {
    return (
      <Paper elevation={0} className="card">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>Loading history...</Typography>
      </Paper>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <TextField
          size="small"
          label="Filter by symbol"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ minWidth: 240 }}
        />
        <Chip label={`${filtered.length} entries`} variant="outlined" sx={{ borderRadius: '999px', fontWeight: 600 }} />
      </div>

      <Paper elevation={0} sx={{ overflow: 'hidden', borderRadius: '28px', border: '1px solid', borderColor: 'divider' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--surface-muted)] text-left">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Symbol</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Date</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Agents</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Recs</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Time</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500">Status</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--outline)' }}>
              {filtered.map((entry) => (
                <tr
                  key={entry.id}
                  className="cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                  onClick={() => router.push(`/history/${entry.id}`)}
                >
                  <td className="px-4 py-3 font-semibold text-[var(--foreground)]">{entry.symbol}</td>
                  <td className="px-4 py-3 text-slate-500">{entry.tradeDate}</td>
                  <td className="px-4 py-3">
                    <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                      {entry.agentSequence.map((agent) => (
                        <Chip
                          key={agent}
                          label={agent.split('-').map((w) => w[0]).join('')}
                          size="small"
                          variant="outlined"
                          title={agent}
                          sx={{ borderRadius: '10px', fontSize: 11 }}
                        />
                      ))}
                    </Stack>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{entry.recommendationsCount}</td>
                  <td className="px-4 py-3 text-slate-500">{entry.executionTime}s</td>
                  <td className="px-4 py-3">
                    <Chip
                      label={entry.success ? 'Success' : 'Failed'}
                      color={entry.success ? 'success' : 'error'}
                      size="small"
                      sx={{ borderRadius: '999px', fontWeight: 700 }}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/symbol/${entry.symbol}`}
                      className="text-xs font-semibold text-[color:#6750A4] hover:opacity-80"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Symbol →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Paper>
    </div>
  );
}
