'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import {
  getMemoryStats,
  getMarketNotes,
  searchMemory,
  type MemoryStats,
  type MarketNoteItem,
  type MemorySearchResult,
} from '@/lib/api';

export default function MemoryPage() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [notes, setNotes] = useState<MarketNoteItem[]>([]);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MemorySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);

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
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-100">Aegis Memory</h1>
              <p className="mt-1 text-sm text-slate-500">
                Semantic search and trading memory
              </p>
            </div>

            {loading && (
              <div className="card">
                <p className="text-sm text-slate-500">Loading memory...</p>
              </div>
            )}

            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard label="Analysis Results" value={stats.analysis_results} />
                <StatCard label="Market Notes" value={stats.market_notes} />
                <StatCard label="Trading Actions" value={stats.trading_actions} />
                <StatCard label="Embedding Dim" value={stats.embedding_dimension} />
              </div>
            )}

            {/* Semantic Search */}
            <div className="card space-y-3">
              <h3 className="text-sm font-semibold text-slate-300">
                Semantic Search
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search analysis results..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-slate-600"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching || !query.trim()}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-2">
                  {searchResults.map((r) => (
                    <div
                      key={r.id}
                      className="rounded-lg bg-slate-800/50 p-3 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-300">
                          ID: {r.id}
                        </span>
                        <span className="text-xs text-emerald-400">
                          {(r.similarity_score * 100).toFixed(1)}% match
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {r.document}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {searchResults.length === 0 && !searching && query && (
                <p className="text-xs text-slate-500">No results found.</p>
              )}
            </div>

            {/* Market Notes */}
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">
                Market Notes ({notes.length})
              </h3>
              {notes.length === 0 ? (
                <p className="text-xs text-slate-500">No market notes yet.</p>
              ) : (
                <div className="space-y-2">
                  {notes.map((note) => (
                    <div
                      key={note.id}
                      className="rounded-lg bg-slate-800/50 p-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-300">
                          {note.symbol || 'General'}
                        </span>
                        <span className="text-xs text-slate-500">
                          {note.note_date}
                        </span>
                      </div>
                      <span className="mt-1 inline-block rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                        {note.category}
                      </span>
                      <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                        {note.content}
                      </p>
                      {note.tags.length > 0 && (
                        <div className="mt-1 flex gap-1">
                          {note.tags.map((tag) => (
                            <span
                              key={tag}
                              className="text-xs text-slate-500"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-200">{value}</p>
    </div>
  );
}
