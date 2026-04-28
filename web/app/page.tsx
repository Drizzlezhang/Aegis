import Header from '@/components/Header';
import MarketIndexCard from '@/components/market-index-card';
import MarketSentimentInline from '@/components/market-sentiment-inline';
import Sidebar from '@/components/Sidebar';
import SymbolCard from '@/components/SymbolCard';
import { getMessage } from '@/i18n/get-message';
import { getMarketIndices, getSymbols, MarketIndexData, SymbolInfo } from '@/lib/api';

export default async function Home() {
  const locale = 'zh-CN';
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
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="card mb-6">
              <h1 className="text-3xl font-bold text-[var(--foreground)]">{getMessage(locale, 'common.dashboard')}</h1>
              <p className="mt-2 text-sm text-slate-500">多 Agent 量化分析总览</p>
            </div>

            {indices.length > 0 && (
              <div className="mb-6">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-[var(--foreground)]">市场指数</h2>
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

            <div className="card-muted mt-6">
              <h2 className="text-sm font-semibold text-[var(--foreground)]">系统状态</h2>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
                <span>Agents: 4 活跃</span>
                <span>Skills: 6 已加载</span>
                <span>最近更新: 刚刚</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
