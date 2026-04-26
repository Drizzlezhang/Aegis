'use client';

import type { StrategyRecommendation } from '@/lib/api';

interface StrategyRecommendationsProps {
  recommendations: StrategyRecommendation[];
}

export default function StrategyRecommendations({ recommendations }: StrategyRecommendationsProps) {
  return (
    <div className="card">
      <h3 className="mb-3 text-sm font-semibold text-slate-300">Strategy Recommendations</h3>
      <div className="space-y-3">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="rounded-lg border border-slate-800 bg-slate-800/30 p-3 transition-colors hover:border-slate-700"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="rounded bg-blue-950 px-2 py-0.5 text-xs font-medium text-blue-400">
                  {rec.type}
                </span>
                <RiskBadge level={rec.riskLevel} />
              </div>
              <span className="text-xs font-medium text-emerald-400">{rec.expectedReturn}</span>
            </div>

            <p className="mt-2 text-sm text-slate-300">{rec.description}</p>

            {(rec.expiration || rec.strike) && (
              <div className="mt-2 flex gap-3 text-xs text-slate-500">
                {rec.expiration && <span>Exp: {rec.expiration}</span>}
                {rec.strike && <span>Strike: {rec.strike}</span>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: StrategyRecommendation['riskLevel'] }) {
  const map: Record<string, string> = {
    low: 'badge-green',
    medium: 'badge-amber',
    high: 'badge-red',
  };
  return <span className={map[level] || 'badge-blue'}>{level}</span>;
}
