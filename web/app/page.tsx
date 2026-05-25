import Header from '@/components/Header';
import MarketIndexCard from '@/components/market-index-card';
import MarketSentimentInline from '@/components/market-sentiment-inline';
import { RealtimeTicker } from '@/components/RealtimeTicker';
import Sidebar from '@/components/Sidebar';
import SymbolCard from '@/components/SymbolCard';
import { getMessage } from '@/i18n/get-message';
import {
  getMarketIndices,
  getSchedulerStatus,
  getSymbols,
  getTrackingStats,
  getWatchlist,
  type MarketIndexData,
  type SymbolInfo,
} from '@/lib/api';

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
  const coreSymbols = symbols.slice(0, 8).map((item) => item.symbol);

  // Quick Cards data (graceful degradation)
  let schedulerStatus: string | null = null;
  let schedulerHighConf: number | null = null;
  let watchlistCount: number | null = null;
  let trackingHitRate: number | null = null;
  let trackingTotal: number | null = null;

  try {
    const sched = await getSchedulerStatus();
    if (sched.lastRunResults.length > 0) {
      const success = sched.lastRunResults.filter((r: { success: boolean }) => r.success).length;
      const total = sched.lastRunResults.length;
      schedulerStatus = `${success}/${total} successful`;
      schedulerHighConf = sched.lastRunResults.filter(
        (r: { recommendationsCount: number }) => r.recommendationsCount > 0
      ).length;
    }
  } catch {
    // scheduler unavailable
  }

  try {
    const wl = await getWatchlist();
    watchlistCount = wl.length;
  } catch {
    // watchlist unavailable
  }

  try {
    const ts = await getTrackingStats();
    trackingHitRate = ts.hitRate;
    trackingTotal = ts.total;
  } catch {
    // tracking unavailable
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

            {/* Quick Cards */}
            <div className="mb-6">
              <div className="grid gap-3 sm:grid-cols-3">
                {/* Scheduler Status Card */}
                <a href="/scheduler" className="card block no-underline transition-colors hover:border-primary/50">
                  <div className="text-xs text-slate-500">
                    {getMessage(locale, 'interaction.dashboardSchedulerSummary')}
                  </div>
                  <div className="mt-2 text-sm text-[var(--foreground)]">
                    {schedulerStatus ?? '—'}
                  </div>
                  {schedulerHighConf != null && (
                    <div className="mt-1 text-xs text-slate-500">
                      {schedulerHighConf} high-confidence recommendations
                    </div>
                  )}
                </a>

                {/* Watchlist Quick Card */}
                <a href="/watchlist" className="card block no-underline transition-colors hover:border-primary/50">
                  <div className="text-xs text-slate-500">
                    {getMessage(locale, 'interaction.dashboardWatchlistCount')}
                  </div>
                  <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                    {watchlistCount != null ? watchlistCount : '—'}
                  </div>
                </a>

                {/* Tracking Summary Card */}
                <a href="/tracking" className="card block no-underline transition-colors hover:border-primary/50">
                  <div className="text-xs text-slate-500">
                    {getMessage(locale, 'interaction.dashboardHitRate')}
                  </div>
                  <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                    {trackingHitRate != null ? `${(trackingHitRate * 100).toFixed(1)}%` : '—'}
                  </div>
                  {trackingTotal != null && (
                    <div className="mt-1 text-xs text-slate-500">
                      {trackingTotal} tracked
                    </div>
                  )}
                </a>
              </div>
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

            <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {symbols.map((s) => (
                  <SymbolCard key={s.symbol} symbol={s} />
                ))}
              </div>

              {coreSymbols.length > 0 && (
                <div className="min-w-0 overflow-x-auto md:overflow-x-visible">
                  <RealtimeTicker symbols={coreSymbols} showVolume locale={locale} />
                </div>
              )}
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