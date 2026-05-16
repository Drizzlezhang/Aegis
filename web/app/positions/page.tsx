import AlertsPanel from '@/components/AlertsPanel';
import Header from '@/components/Header';
import PipelineHealth from '@/components/PipelineHealth';
import PositionTable from '@/components/PositionTable';
import Sidebar from '@/components/Sidebar';
import { getPositionSummary, getStatus, getSymbols, type PipelineMetrics, type PositionSummaryData, type SymbolInfo } from '@/lib/api';

export default async function PositionsPage() {
  let symbols: SymbolInfo[] = [];
  let summary: PositionSummaryData | null = null;
  let pipeline: PipelineMetrics | null = null;

  try {
    symbols = await getSymbols();
  } catch {
    symbols = [];
  }

  try {
    summary = await getPositionSummary();
  } catch {
    summary = null;
  }

  try {
    const status = await getStatus();
    pipeline = status.pipeline;
  } catch {
    pipeline = null;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-6xl space-y-4">
            <PositionTable positions={summary?.positions ?? []} summary={summary} />
            <AlertsPanel />
            <PipelineHealth pipeline={pipeline} />
          </div>
        </main>
      </div>
    </div>
  );
}
