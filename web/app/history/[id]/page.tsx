import { notFound } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { AnalysisReport } from '@/components/AnalysisReport';
import { getAnalysisDetail, type AnalysisDetail } from '@/lib/api';
import { isStructuredReport } from '@/lib/type-guards';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function HistoryDetailPage({ params }: PageProps) {
  const { id } = await params;
  const analysisId = Number(id);
  if (Number.isNaN(analysisId)) {
    notFound();
  }

  let detail: AnalysisDetail;
  try {
    detail = await getAnalysisDetail(analysisId);
  } catch {
    notFound();
  }

  const recommendations = detail.recommendations || [];
  const structuredReport = detail.metadata?.structured_report;
  const hasStructuredReport = isStructuredReport(structuredReport);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-5xl space-y-4">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Link href="/history" className="hover:text-slate-300">History</Link>
              <span>/</span>
              <span className="text-slate-300">Analysis #{detail.id}</span>
            </div>

            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`h-2 w-2 rounded-full ${
                    detail.success ? 'bg-emerald-500' : 'bg-rose-500'
                  }`}
                />
                <h1 className="text-2xl font-bold text-slate-100">
                  {detail.symbol}
                </h1>
                <span className="rounded-lg bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                  {detail.tradeDate}
                </span>
              </div>
              <Link
                href={`/symbol/${detail.symbol}`}
                className="text-sm font-medium text-blue-400 hover:text-blue-300"
              >
                View Symbol →
              </Link>
            </div>

            {/* Agent Sequence */}
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">Agent Sequence</h3>
              <div className="flex flex-wrap items-center gap-2">
                {detail.agentSequence.map((agent, idx) => (
                  <span key={agent} className="flex items-center gap-1 text-xs">
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">{agent}</span>
                    {idx < detail.agentSequence.length - 1 && (
                      <span className="text-slate-600">→</span>
                    )}
                  </span>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <div className="card">
                <h3 className="mb-3 text-sm font-semibold text-slate-300">
                  Strategy Recommendations ({recommendations.length})
                </h3>
                <div className="space-y-3">
                  {recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-800/30 p-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="rounded bg-blue-950 px-2 py-0.5 text-xs font-medium text-blue-400">
                          {rec.type}
                        </span>
                        <span className="text-xs text-slate-400">
                          {Math.round((rec.confidence || 0) * 100)}% confidence
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-400">
                        <div>
                          Strike:{' '}
                          <span className="text-slate-200">${rec.strike}</span>
                        </div>
                        <div>
                          Expiry:{' '}
                          <span className="text-slate-200">{rec.expiry}</span>
                        </div>
                        <div>
                          Entry:{' '}
                          <span className="text-slate-200">${rec.entry_price}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Report */}
            {hasStructuredReport && (
              <div className="card">
                <h3 className="mb-3 text-sm font-semibold text-slate-300">Structured Report</h3>
                <AnalysisReport
                  report={structuredReport}
                  defaultExpanded={['executive_summary']}
                />
              </div>
            )}

            {detail.actionReport && (
              <div className="card">
                <h3 className="mb-3 text-sm font-semibold text-slate-300">Agent Report</h3>
                <pre className="text-xs text-slate-400 leading-relaxed whitespace-pre-wrap font-mono">
                  {detail.actionReport}
                </pre>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
