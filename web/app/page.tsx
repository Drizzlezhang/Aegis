import Header from '@/components/Header';
import MarketIndexCard from '@/components/market-index-card';
import MarketSentimentInline from '@/components/market-sentiment-inline';
import Sidebar from '@/components/Sidebar';
import SymbolCard from '@/components/SymbolCard';
import { getMarketIndices, getSymbols, MarketIndexData, SymbolInfo } from '@/lib/api';

export default async function Home() {
  let symbols: SymbolInfo[] = [];
  let indices: MarketIndexData[] = [];
  try {
    symbols = await getSymbols();
  } catch {
    symbols = [];
  }
  try {
    const marketResp = await getMarketIndices();
    indices = marketResp.indices || [];
  } catch {
    indices = [];
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
              <p className="mt-1 text-sm text-slate-500">
                Multi-Agent quantitative analysis overview
              </p>
            </div>

            {indices.length > 0 && (
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-300">Market Indices</h2>
                  <MarketSentimentInline indices={indices} />
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                  {indices.map((idx) => (
                    <MarketIndexCard
                      key={idx.symbol}
                      symbol={idx.symbol}
                      name={idx.name}
                      price={idx.price}
                      change={idx.change}
                      change_percent={idx.change_percent}
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {symbols.map((s) => (
                <SymbolCard key={s.symbol} symbol={s} />
              ))}
            </div>

            <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
              <h2 className="text-sm font-semibold text-slate-300">System Status</h2>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
                <span>Agents: 4 active</span>
                <span>Skills: 6 loaded</span>
                <span>Last update: just now</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
