'use client';

import { Chip, Paper, Stack, Typography } from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import type { PipelineMetrics } from '@/lib/api';
import { useLocale } from './LocaleProvider';

const PIPELINE_AGENTS = [
  'Data-Harvester',
  'Quant-Brain',
  'Investment-Debate',
  'Strategy-Execution',
  'Aegis-Memory',
  'Position-Monitor',
];

export default function PipelineHealth({ pipeline }: { pipeline: PipelineMetrics | null }) {
  const { locale } = useLocale();

  if (!pipeline) {
    return (
      <Paper elevation={0} className="card">
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.pipeline_title')}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1.5, color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.pipeline_no_data')}
        </Typography>
      </Paper>
    );
  }

  const lastRun = pipeline.last_run_time
    ? new Date(pipeline.last_run_time).toLocaleString()
    : getMessage(locale, 'interaction.pipeline_never_run');

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
        {getMessage(locale, 'interaction.pipeline_title')}
      </Typography>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {PIPELINE_AGENTS.map((agent) => (
          <Chip key={agent} label={agent} size="small" variant="outlined" />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricItem label={getMessage(locale, 'interaction.pipeline_total_runs')} value={String(pipeline.total_runs)} />
        <MetricItem label={getMessage(locale, 'interaction.pipeline_last_run')} value={lastRun} />
        <MetricItem label={getMessage(locale, 'interaction.pipeline_avg_duration')} value={`${pipeline.avg_duration_seconds.toFixed(3)}s`} />
        <MetricItem label={getMessage(locale, 'interaction.pipeline_llm_requests')} value={String(pipeline.llm.requests)} />
        <MetricItem label={getMessage(locale, 'interaction.pipeline_llm_tokens')} value={String(pipeline.llm.tokens)} />
        <MetricItem label={getMessage(locale, 'interaction.pipeline_llm_errors')} value={String(pipeline.llm.errors)} />
      </div>
    </Paper>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <Paper elevation={0} className="card-muted">
      <Stack spacing={0.5}>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          {label}
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {value}
        </Typography>
      </Stack>
    </Paper>
  );
}
