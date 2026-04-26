import { notFound } from 'next/navigation';
import GEXChart from '@/components/gex-chart';
import Header from '@/components/Header';
import MarketSentimentBanner from '@/components/market-sentiment-banner';
import PriceChart from '@/components/price-chart';
import Sidebar from '@/components/Sidebar';
import SupportResistance from '@/components/SupportResistance';
import StrategyRecommendations from '@/components/StrategyRecommendations';
import VolumeProfileChart from '@/components/volume-profile-chart';
import SymbolAnalysisPanel from '@/components/SymbolAnalysisPanel';
import { getMarketIndices, getSymbolDetail, MarketIndexData } from '@/lib/api';

interface PageProps {
  params: Promise<{ symbol: string }>;
}

export default async function SymbolPage({ params }: PageProps) {
  const { symbol } = await params;
  let detail;
  let indices: MarketIndexData[] = [];

  try {
    detail = await getSymbolDetail(symbol.toUpperCase());
  } catch {
    notFound();
  }

  try {
    const marketResp = await getMarketIndices();
    indices = marketResp.indices || [];
  } catch {
    indices = [];
  }

  const positive = detail.change >= 0;

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            {/* Market Sentiment Banner */}
            {indices.length > 0 && (
              <MarketSentimentBanner indices={indices} />
            )}

            {/* Header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-100">
                  {detail.symbol}
                </h1>
                <p className="text-sm text-slate-500">{detail.name}</p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-semibold text-slate-100">
                  ${detail.price.toFixed(2)}
                </p>
                <p
                  className={`text-sm font-medium ${
                    positive ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {positive ? '+' : ''}
                  {detail.change.toFixed(2)} ({positive ? '+' : ''}
                  {detail.changePercent.toFixed(2)}%)
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Volume" value={detail.volume.toLocaleString()} />
              <StatCard label="Avg Volume" value={detail.avgVolume.toLocaleString()} />
              <StatCard label="Market Cap" value={detail.marketCap} />
              <StatCard label="P/E Ratio" value={detail.peRatio.toString()} />
            </div>

            {/* Charts */}
            <div className="grid gap-4 lg:grid-cols-2">
              <PriceChart
                currentPrice={detail.price}
                supports={detail.supports}
                resistances={detail.resistances}
              />
              <VolumeProfileChart
                poc={detail.volumeProfile.poc}
                vah={detail.volumeProfile.vah}
                val={detail.volumeProfile.val}
                volumeAtPoc={detail.volumeProfile.volumeAtPoc}
                currentPrice={detail.price}
              />
            </div>

            <GEXChart walls={detail.gexWalls} currentPrice={detail.price} />

            {/* Support / Resistance */}
            <SupportResistance
              supports={detail.supports}
              resistances={detail.resistances}
              currentPrice={detail.price}
            />

            {/* Live Multi-Agent Analysis */}
            <SymbolAnalysisPanel symbol={detail.symbol} />

            {/* Static Strategy Recommendations */}
            <StrategyRecommendations recommendations={detail.recommendations} />
          </div>
        </main>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-200">{value}</p>
    </div>
  );
}
