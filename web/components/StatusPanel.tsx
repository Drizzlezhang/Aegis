'use client';

import { useEffect, useState } from 'react';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
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
      <Paper elevation={0} className="card">
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.loadingSystemStatus')}
        </Typography>
      </Paper>
    );
  }

  if (!data) {
    return (
      <Paper elevation={0} className="card">
        <Typography variant="body2" sx={{ color: 'error.main' }}>
          {getMessage(locale, 'interaction.failedToLoadSystemStatus')}
        </Typography>
      </Paper>
    );
  }

  const allHealthy = Object.values(data.health).every((v) => v);

  return (
    <Stack spacing={3}>
      <Paper elevation={0} className="card">
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {getMessage(locale, 'interaction.healthOverview')}
          </Typography>
          <Chip
            label={allHealthy ? getMessage(locale, 'interaction.allSystemsOperational') : getMessage(locale, 'interaction.issuesDetected')}
            color={allHealthy ? 'success' : 'error'}
            variant="filled"
            sx={{ fontWeight: 700, borderRadius: '999px' }}
          />
        </Stack>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(data.health).map(([key, value]) => (
            <HealthItem key={key} name={key} healthy={value} />
          ))}
        </div>
      </Paper>

      <div className="grid gap-4 md:grid-cols-2">
        <Paper elevation={0} className="card">
          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
            {getMessage(locale, 'interaction.agents')}
          </Typography>
          <Stack spacing={2}>
            {data.agents.map((agent) => (
              <Box
                key={agent.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 2,
                  p: 2,
                  borderRadius: '20px',
                  bgcolor: 'action.hover',
                }}
              >
                <div>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                    {agent.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {getMessage(locale, 'interaction.lastRun')}: {new Date(agent.lastRun).toLocaleTimeString()}
                  </Typography>
                </div>
                <div className="text-right">
                  <AgentStatusBadge status={agent.status} />
                  <Typography variant="caption" sx={{ mt: 0.5, display: 'block', color: 'text.secondary' }}>
                    {agent.executions} {getMessage(locale, 'interaction.runs')}
                  </Typography>
                </div>
              </Box>
            ))}
          </Stack>
        </Paper>

        <Paper elevation={0} className="card">
          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
            {getMessage(locale, 'interaction.skills')}
          </Typography>
          <Stack spacing={2}>
            {data.skills.map((skill) => (
              <Box
                key={skill.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 2,
                  p: 2,
                  borderRadius: '20px',
                  bgcolor: 'action.hover',
                }}
              >
                <div>
                  <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                    {skill.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {skill.type}
                  </Typography>
                </div>
                <Chip
                  label={skill.loaded ? getMessage(locale, 'interaction.loaded') : getMessage(locale, 'common.error')}
                  color={skill.loaded ? 'success' : 'error'}
                  variant="filled"
                  sx={{ fontWeight: 700, borderRadius: '999px' }}
                />
              </Box>
            ))}
          </Stack>
        </Paper>
      </div>

      <Paper elevation={0} className="card">
        <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.systemInfo')}
        </Typography>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <InfoItem label={getMessage(locale, 'interaction.version')} value={data.system.version} />
          <InfoItem label={getMessage(locale, 'interaction.uptime')} value={data.system.uptime} />
          <InfoItem label={getMessage(locale, 'interaction.memory')} value={data.system.memoryUsage} />
          <InfoItem label={getMessage(locale, 'interaction.python')} value={data.system.pythonVersion} />
          <InfoItem label="Node.js" value={data.system.nodeVersion} />
        </div>
      </Paper>
    </Stack>
  );
}

function HealthItem({ name, healthy }: { name: string; healthy: boolean }) {
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: '18px', bgcolor: 'action.hover', textAlign: 'center' }}>
      <div className={`mx-auto h-2.5 w-2.5 rounded-full ${healthy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'text.secondary', textTransform: 'capitalize' }}>
        {name.replace('_', ' ')}
      </Typography>
    </Paper>
  );
}

function AgentStatusBadge({ status }: { status: string }) {
  const map: Record<string, 'success' | 'warning' | 'error' | 'primary'> = {
    idle: 'success',
    running: 'warning',
    error: 'error',
  };

  return (
    <Chip
      label={status}
      color={map[status] || 'primary'}
      variant="filled"
      size="small"
      sx={{ fontWeight: 700, borderRadius: '999px', textTransform: 'capitalize' }}
    />
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <Paper elevation={0} sx={{ p: 1.5, borderRadius: '18px', bgcolor: 'action.hover' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 700, color: 'text.primary' }}>
        {value}
      </Typography>
    </Paper>
  );
}
