import { notFound } from 'next/navigation';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getChangeColorClasses } from '@/lib/change-color';
import { getMarketIndices, getSymbols, type MarketIndexData, type SymbolInfo } from '@/lib/api';
import { parseMarketContext, getSentimentStyle, getVixStyle } from '@/lib/market-context';

export default async function MarketPage() {
  let indices: MarketIndexData[] = [];
  let symbols: SymbolInfo[] = [];
  let error: string | null = null;

  try {
    const resp = await getMarketIndices();
    indices = resp.indices || [];
    error = resp.error || null;
  } catch {
    notFound();
  }

  try {
    symbols = await getSymbols();
  } catch {
    symbols = [];
  }

  const ctx = parseMarketContext(indices);
  const sentiment = getSentimentStyle(ctx.sentiment);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            <div className="card">
              <h1 className="text-3xl font-bold text-[var(--foreground)]">市场概览</h1>
              <p className="mt-2 text-sm text-slate-500">实时市场指数与情绪概览</p>
            </div>

            {error && (
              <div className="card">
                <p className="text-sm text-rose-400">错误: {error}</p>
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="card text-center">
                <p className="text-xs text-slate-500">市场情绪</p>
                <span className={`mt-2 inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${sentiment.bg} ${sentiment.text}`}>
                  {sentiment.label}
                </span>
              </div>
              <div className="card text-center">
                <p className="text-xs text-slate-500">VIX 水平</p>
                <p className={`mt-2 text-lg font-semibold ${getVixStyle(ctx.regime)}`}>
                  {ctx.vix !== null ? ctx.vix.toFixed(2) : '—'}
                </p>
              </div>
              <div className="card text-center">
                <p className="text-xs text-slate-500">仓位建议</p>
                <p className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                  {ctx.positionFactor === 1.0 ? '100%' : `${(ctx.positionFactor * 100).toFixed(0)}%`}
                </p>
              </div>
            </div>

            {ctx.warning && (
              <div className="card-muted border-amber-300/40 bg-amber-500/10">
                <p className="text-sm font-medium text-amber-500">{ctx.warning}</p>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {indices.map((idx) => {
                const positive = idx.change >= 0;
                const changeColors = getChangeColorClasses(positive);
                return (
                  <div key={idx.symbol} className="card">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold text-[var(--foreground)]">{idx.name}</p>
                        <p className="text-xs text-slate-500">{idx.symbol}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-[var(--foreground)]">{idx.price.toFixed(2)}</p>
                        <p className={`text-xs font-medium ${changeColors.text}`}>
                          {positive ? '+' : ''}{idx.change.toFixed(2)} ({positive ? '+' : ''}{idx.change_percent.toFixed(2)}%)
                        </p>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{new Date(idx.timestamp).toLocaleString()}</p>
                  </div>
                );
              })}
            </div>

            {indices.length === 0 && !error && (
              <div className="card">
                <p className="text-sm text-slate-500">暂无市场数据。</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
