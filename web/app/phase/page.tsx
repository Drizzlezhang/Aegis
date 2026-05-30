import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { getSymbols, type SymbolInfo } from '@/lib/api';

export default async function PhasePage() {
  let symbols: SymbolInfo[] = [];
  try { symbols = await getSymbols(); } catch { symbols = []; }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="card mb-6">
              <h1 className="text-3xl font-bold text-[var(--foreground)]">实时面板</h1>
              <p className="mt-2 text-sm text-slate-500">实时行情与信号监控</p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="card">
                <h2 className="text-lg font-semibold mb-3">核心标的</h2>
                <div className="space-y-2">
                  {symbols.slice(0, 8).map((s) => (
                    <div key={s.symbol} className="flex items-center justify-between rounded-lg border border-[var(--outline)] p-3">
                      <div>
                        <span className="font-semibold">{s.symbol}</span>
                        <span className="ml-2 text-xs text-slate-500">{s.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-semibold">${s.price.toFixed(2)}</div>
                        <div className={`text-xs font-medium ${s.change >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                          {s.change >= 0 ? '+' : ''}{s.changePercent.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <h2 className="text-lg font-semibold mb-3">信号监控</h2>
                <p className="text-sm text-slate-500">实时信号将在分析运行时显示</p>
                <div className="mt-4 rounded-lg border border-dashed border-[var(--outline)] p-8 text-center">
                  <p className="text-slate-400">暂无活跃信号</p>
                  <p className="mt-1 text-xs text-slate-400">运行分析以生成交易信号</p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
