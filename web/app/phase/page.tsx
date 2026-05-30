'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { SymbolPicker } from '@/components/PhasePanel/SymbolPicker';
import { PhaseCurrentCard } from '@/components/PhasePanel/PhaseCurrentCard';
import { PhaseHistory } from '@/components/PhasePanel/PhaseHistory';
import { usePhaseStream } from '@/hooks/usePhaseStream';
import { getSymbols, type SymbolInfo } from '@/lib/api';

export default function PhasePage() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const { status, currentPhase, phaseHistory, setSymbol } = usePhaseStream();

  useEffect(() => {
    void getSymbols().then(setSymbols).catch(() => setSymbols([]));
  }, []);

  const selectedSymbol = currentPhase?.symbol ?? '';

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-[var(--foreground)]">实时面板</h1>
                <p className="mt-2 text-sm text-slate-500">实时行情与信号监控</p>
              </div>
              <SymbolPicker
                symbols={symbols}
                selected={selectedSymbol}
                onSelect={setSymbol}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <PhaseCurrentCard
                phase={currentPhase}
                status={status}
                symbol={selectedSymbol}
              />
              <PhaseHistory history={phaseHistory} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
