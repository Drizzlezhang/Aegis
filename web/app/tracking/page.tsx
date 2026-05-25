import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import TrackingContent from '@/components/TrackingContent';
import { getSymbols } from '@/lib/api';
import {
  getTrackingStats,
  getTrackedDecisions,
  type SymbolInfo,
  type TrackingStats,
  type TrackedDecision,
} from '@/lib/api';

export default async function TrackingPage() {
  let symbols: SymbolInfo[] = [];
  let stats: TrackingStats | null = null;
  let decisions: TrackedDecision[] | null = null;

  try {
    symbols = await getSymbols();
  } catch {
    symbols = [];
  }

  try {
    stats = await getTrackingStats();
  } catch {
    stats = null;
  }

  try {
    decisions = await getTrackedDecisions(20);
  } catch {
    decisions = null;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <TrackingContent initialStats={stats} initialDecisions={decisions} />
        </main>
      </div>
    </div>
  );
}