import dynamic from 'next/dynamic';
import { notFound } from 'next/navigation';
import { Chip, Paper, Typography } from '@mui/material';
import GEXChart from '@/components/gex-chart';
import Header from '@/components/Header';
import MarketSentimentBanner from '@/components/market-sentiment-banner';
import PriceChart from '@/components/price-chart';
import Sidebar from '@/components/Sidebar';
import SupportResistance from '@/components/SupportResistance';
import StrategyRecommendations from '@/components/StrategyRecommendations';
import VolumeProfileChart from '@/components/volume-profile-chart';
import { getChangeColorClasses } from '@/lib/change-color';
import { getMarketIndices, getSymbolDetail, getSymbols, loadSymbolPageData, MarketIndexData, SymbolInfo } from '@/lib/api';

const LazySymbolAnalysisPanel = dynamic(() => import('@/components/SymbolAnalysisPanel'), {
  loading: () => (
    <div className="card">
      <p className="text-sm text-slate-400">Loading analysis panel...</p>
    </div>
  ),
});

interface PageProps {
  params: Promise<{ symbol: string }>;
}

export default async function SymbolPage({ params }: PageProps) {
  const { symbol } = await params;
  let detail;
  let indices: MarketIndexData[] = [];
  let symbols: SymbolInfo[] = [];

  try {
    const data = await loadSymbolPageData(symbol, {
      getSymbolDetail,
      getMarketIndices,
      getSymbols,
    });
    detail = data.detail;
    indices = data.indices;
    symbols = data.symbols;
  } catch {
    notFound();
  }

  const positive = detail.change >= 0;
  const changeColors = getChangeColorClasses(positive);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            {indices.length > 0 && <MarketSentimentBanner indices={indices} />}

            <Paper elevation={0} className="card">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-[var(--foreground)]">{detail.symbol}</h1>
                  <p className="text-sm text-slate-500">{detail.name}</p>
                </div>
                <div className="text-left sm:text-right">
                  <p className="text-3xl font-semibold text-[var(--foreground)]">${detail.price.toFixed(2)}</p>
                  <p className={`text-sm font-medium ${changeColors.text}`}>
                    {positive ? '+' : ''}
                    {detail.change.toFixed(2)} ({positive ? '+' : ''}
                    {detail.changePercent.toFixed(2)}%)
                  </p>
                </div>
              </div>
            </Paper>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Volume" value={detail.volume.toLocaleString()} />
              <StatCard label="Avg Volume" value={detail.avgVolume.toLocaleString()} />
              <StatCard label="Market Cap" value={detail.marketCap} />
              <StatCard label="P/E Ratio" value={detail.peRatio.toString()} />
            </div>

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

            <SupportResistance
              supports={detail.supports}
              resistances={detail.resistances}
              currentPrice={detail.price}
            />

            <LazySymbolAnalysisPanel symbol={detail.symbol} />

            <StrategyRecommendations recommendations={detail.recommendations} />
          </div>
        </main>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Paper elevation={0} className="card-muted">
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ mt: 1, fontWeight: 700, color: 'text.primary' }}>
        {value}
      </Typography>
    </Paper>
  );
}
