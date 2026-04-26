import { notFound } from 'next/navigation';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getMarketIndices, type MarketIndexData } from '@/lib/api';
import { parseMarketContext, getSentimentStyle, getVixStyle } from '@/lib/market-context';

export default async function MarketPage() {
  let indices: MarketIndexData[] = [];
  let error: string | null = null;

  try {
    const resp = await getMarketIndices();
    indices = resp.indices || [];
    error = resp.error || null;
  } catch {
    notFound();
  }

  const ctx = parseMarketContext(indices);
  const sentiment = getSentimentStyle(ctx.sentiment);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-100">Market Overview</h1>
              <p className="mt-1 text-sm text-slate-500">Real-time market indices and sentiment</p>
            </div>

            {error && (
              <div className="card">
                <p className="text-sm text-rose-400">Error: {error}</p>
              </div>
            )}

            {/* Sentiment Overview */}
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="card text-center">
                <p className="text-xs text-slate-500">Market Sentiment</p>
                <span className={`mt-2 inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${sentiment.bg} ${sentiment.text}`}>
                  {sentiment.label}
                </span>
              </div>
              <div className="card text-center">
                <p className="text-xs text-slate-500">VIX Level</p>
                <p className={`mt-2 text-lg font-semibold ${getVixStyle(ctx.regime)}`}>
                  {ctx.vix !== null ? ctx.vix.toFixed(2) : '—'}
                </p>
              </div>
              <div className="card text-center">
                <p className="text-xs text-slate-500">Position Sizing</p>
                <p className="mt-2 text-lg font-semibold text-slate-200">
                  {ctx.positionFactor === 1.0 ? '100%' : `${(ctx.positionFactor * 100).toFixed(0)}%`}
                </p>
              </div>
            </div>

            {/* Warning */}
            {ctx.warning && (
              <div className="rounded-xl border border-amber-800 bg-amber-900/20 p-4">
                <p className="text-sm font-medium text-amber-400">{ctx.warning}</p>
              </div>
            )}

            {/* Index Cards */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {indices.map((idx) => {
                const positive = idx.change >= 0;
                return (
                  <div key={idx.symbol} className="card">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-200">{idx.name}</p>
                        <p className="text-xs text-slate-500">{idx.symbol}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-slate-100">
                          {idx.price.toFixed(2)}
                        </p>
                        <p className={`text-xs font-medium ${positive ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {positive ? '+' : ''}{idx.change.toFixed(2)} ({positive ? '+' : ''}{idx.change_percent.toFixed(2)}%)
                        </p>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-slate-600">
                      {new Date(idx.timestamp).toLocaleString()}
                    </p>
                  </div>
                );
              })}
            </div>

            {indices.length === 0 && !error && (
              <div className="card">
                <p className="text-sm text-slate-500">No market data available.</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
