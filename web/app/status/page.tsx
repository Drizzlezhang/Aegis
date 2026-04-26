import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import StatusPanel from '@/components/StatusPanel';
import { getSymbols, type SymbolInfo } from '@/lib/api';

export default async function StatusPage() {
  let symbols: SymbolInfo[] = [];

  try {
    symbols = await getSymbols();
  } catch {
    symbols = [];
  }
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-slate-100">System Status</h1>
              <p className="mt-1 text-sm text-slate-500">
                Agent health, skills, and system metrics
              </p>
            </div>
            <StatusPanel />
          </div>
        </main>
      </div>
    </div>
  );
}
