'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface HistoryEntry {
  id: number;
  symbol: string;
  tradeDate: string;
  agentSequence: string[];
  recommendationsCount: number;
  executionTime: number;
  success: boolean;
}

export default function HistoryTable() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    fetch('/api/analysis')
      .then((res) => res.json())
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
      <div className="card">
        <p className="text-sm text-slate-500">Loading history...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Filter by symbol..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-slate-700"
        />
        <span className="text-xs text-slate-500">{filtered.length} entries</span>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/80 text-left">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Symbol</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Date</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Agents</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Recs</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Time</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500">Status</th>
              <th className="px-4 py-2 text-xs font-medium text-slate-500"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {filtered.map((entry) => (
              <tr key={entry.id} className="hover:bg-slate-900/50">
                <td className="px-4 py-2 font-medium text-slate-200">{entry.symbol}</td>
                <td className="px-4 py-2 text-slate-500">{entry.tradeDate}</td>
                <td className="px-4 py-2">
                  <div className="flex gap-1">
                    {entry.agentSequence.map((agent) => (
                      <span
                        key={agent}
                        className="inline-block rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400"
                        title={agent}
                      >
                        {agent.split('-').map((w) => w[0]).join('')}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2 text-slate-400">{entry.recommendationsCount}</td>
                <td className="px-4 py-2 text-slate-500">{entry.executionTime}s</td>
                <td className="px-4 py-2">
                  {entry.success ? (
                    <span className="badge-green text-xs">Success</span>
                  ) : (
                    <span className="badge-red text-xs">Failed</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <Link
                    href={`/symbol/${entry.symbol}`}
                    className="text-xs font-medium text-blue-400 hover:text-blue-300"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
