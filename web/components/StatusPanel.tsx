'use client';

import { useEffect, useState } from 'react';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from './LocaleProvider';

interface AgentStatus {
  name: string;
  status: string;
  lastRun: string;
  executions: number;
}

interface SkillStatus {
  name: string;
  type: string;
  loaded: boolean;
}

interface SystemInfo {
  version: string;
  uptime: string;
  memoryUsage: string;
  pythonVersion: string;
  nodeVersion: string;
}

interface HealthStatus {
  data_harvester: boolean;
  quant_brain: boolean;
  strategy_exec: boolean;
  aegis_memory: boolean;
  llm_router: boolean;
  vector_store: boolean;
}

interface StatusData {
  agents: AgentStatus[];
  skills: SkillStatus[];
  system: SystemInfo;
  health: HealthStatus;
}

export default function StatusPanel() {
  const [data, setData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const { locale } = useLocale();

  useEffect(() => {
    fetch('/api/status')
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card">
        <p className="text-sm text-slate-500">{getMessage(locale, 'interaction.loadingSystemStatus')}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card">
        <p className="text-sm text-rose-400">{getMessage(locale, 'interaction.failedToLoadSystemStatus')}</p>
      </div>
    );
  }

  const allHealthy = Object.values(data.health).every((v) => v);

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-300">{getMessage(locale, 'interaction.healthOverview')}</h3>
          <span className={allHealthy ? 'badge-green' : 'badge-red'}>
            {allHealthy ? getMessage(locale, 'interaction.allSystemsOperational') : getMessage(locale, 'interaction.issuesDetected')}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(data.health).map(([key, value]) => (
            <HealthItem key={key} name={key} healthy={value} />
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">{getMessage(locale, 'interaction.agents')}</h3>
          <div className="space-y-2">
            {data.agents.map((agent) => (
              <div
                key={agent.name}
                className="flex items-center justify-between rounded-lg bg-slate-800/50 p-2"
              >
                <div>
                  <p className="text-sm font-medium text-slate-200">{agent.name}</p>
                  <p className="text-xs text-slate-500">
                    {getMessage(locale, 'interaction.lastRun')}: {new Date(agent.lastRun).toLocaleTimeString()}
                  </p>
                </div>
                <div className="text-right">
                  <AgentStatusBadge status={agent.status} />
                  <p className="mt-0.5 text-xs text-slate-500">{agent.executions} {getMessage(locale, 'interaction.runs')}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">{getMessage(locale, 'interaction.skills')}</h3>
          <div className="space-y-2">
            {data.skills.map((skill) => (
              <div
                key={skill.name}
                className="flex items-center justify-between rounded-lg bg-slate-800/50 p-2"
              >
                <div>
                  <p className="text-sm font-medium text-slate-200">{skill.name}</p>
                  <p className="text-xs text-slate-500">{skill.type}</p>
                </div>
                <span className={skill.loaded ? 'badge-green' : 'badge-red'}>
                  {skill.loaded ? getMessage(locale, 'interaction.loaded') : getMessage(locale, 'common.error')}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-slate-300">{getMessage(locale, 'interaction.systemInfo')}</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <InfoItem label={getMessage(locale, 'interaction.version')} value={data.system.version} />
          <InfoItem label={getMessage(locale, 'interaction.uptime')} value={data.system.uptime} />
          <InfoItem label={getMessage(locale, 'interaction.memory')} value={data.system.memoryUsage} />
          <InfoItem label={getMessage(locale, 'interaction.python')} value={data.system.pythonVersion} />
          <InfoItem label="Node.js" value={data.system.nodeVersion} />
        </div>
      </div>
    </div>
  );
}

function HealthItem({ name, healthy }: { name: string; healthy: boolean }) {
  return (
    <div className="rounded-lg bg-slate-800/50 p-2 text-center">
      <div className={`mx-auto h-2 w-2 rounded-full ${healthy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      <p className="mt-1 text-xs capitalize text-slate-400">{name.replace('_', ' ')}</p>
    </div>
  );
}

function AgentStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    idle: 'badge-green',
    running: 'badge-amber',
    error: 'badge-red',
  };
  return <span className={map[status] || 'badge-blue'}>{status}</span>;
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-800/50 p-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-slate-200">{value}</p>
    </div>
  );
}
