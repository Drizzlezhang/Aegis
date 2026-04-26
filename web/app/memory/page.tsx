import Header from '@/components/Header';
import MemoryPageContent from '@/components/MemoryPageContent';
import Sidebar from '@/components/Sidebar';
import { getSymbols, type SymbolInfo } from '@/lib/api';

export default async function MemoryPage() {
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
          <MemoryPageContent />
        </main>
      </div>
    </div>
  );
}
