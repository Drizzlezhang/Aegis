import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import AnalyzeForm from '@/components/AnalyzeForm';

export default function AnalyzePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-2xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-slate-100">Run Analysis</h1>
              <p className="mt-1 text-sm text-slate-500">
                Trigger multi-agent analysis for a symbol
              </p>
            </div>
            <AnalyzeForm />
          </div>
        </main>
      </div>
    </div>
  );
}
