'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, LinearProgress, Paper, Stack, Typography } from '@mui/material';
import {
  runAnalysisStream,
  type AnalysisResult,
  type AnalysisStreamProgressEvent,
  type AnalysisStreamStepEvent,
} from '@/lib/api';
import { getMessage } from '@/i18n/get-message';
import { useLocale } from './LocaleProvider';

type StepStatus = 'pending' | 'running' | 'done' | 'error';
type StepKey = 'data_harvester' | 'quant_brain' | 'strategy' | 'memory';

type StepView = { key: StepKey; status: StepStatus; elapsedMs: number | null };

const STEP_ORDER: StepKey[] = ['data_harvester', 'quant_brain', 'strategy', 'memory'];

const STEP_AGENT_MAP: Record<string, StepKey> = {
  dataharvester: 'data_harvester',
  datacollection: 'data_harvester',
  quantbrain: 'quant_brain',
  quantitativeanalysis: 'quant_brain',
  strategyexecution: 'strategy',
  strategyexec: 'strategy',
  memorylogging: 'memory',
  aegismemory: 'memory',
};

const STEP_LABEL_KEYS: Record<
  StepKey,
  'interaction.step_data_harvester' | 'interaction.step_quant_brain' | 'interaction.step_strategy' | 'interaction.step_memory'
> = {
  data_harvester: 'interaction.step_data_harvester',
  quant_brain: 'interaction.step_quant_brain',
  strategy: 'interaction.step_strategy',
  memory: 'interaction.step_memory',
};

const STATUS_LABEL_KEYS: Record<
  StepStatus,
  'interaction.status_pending' | 'interaction.status_running' | 'interaction.status_done' | 'interaction.status_error'
> = {
  pending: 'interaction.status_pending',
  running: 'interaction.status_running',
  done: 'interaction.status_done',
  error: 'interaction.status_error',
};

export type AnalysisProgressCompletePayload = {
  results: AnalysisResult[];
  totalTime: number;
  progress: number;
};

type AnalysisProgressProps = {
  symbols: string[];
  onComplete: (payload: AnalysisProgressCompletePayload) => void;
  onError: (error: string) => void;
  autoStart?: boolean;
};

function statusIcon(status: StepStatus): string {
  if (status === 'running') return '🔄';
  if (status === 'done') return '✅';
  if (status === 'error') return '❌';
  return '⏳';
}

function formatElapsed(elapsedMs: number | null): string {
  if (elapsedMs === null) return '--';
  if (elapsedMs < 1000) return `${elapsedMs}ms`;
  return `${(elapsedMs / 1000).toFixed(1)}s`;
}

function normalizeStageToStepIndex(stage: string, fallbackIndex: number): number {
  const normalized = stage.toLowerCase().replace(/[^a-z]/g, '');
  const key = STEP_AGENT_MAP[normalized];
  if (!key) return fallbackIndex;
  return STEP_ORDER.indexOf(key);
}

function nextStepsByIndex(prev: StepView[], index: number, nowMs: number, markError = false): StepView[] {
  return prev.map((step, i) => {
    if (i < index) {
      if (step.status === 'done') return step;
      return { ...step, status: 'done', elapsedMs: step.elapsedMs ?? nowMs };
    }
    if (i === index) {
      if (markError) return { ...step, status: 'error', elapsedMs: step.elapsedMs ?? nowMs };
      if (step.status === 'done') return step;
      return { ...step, status: 'running' };
    }
    if (step.status === 'done') return step;
    return { ...step, status: 'pending', elapsedMs: step.status === 'pending' ? step.elapsedMs : null };
  });
}

export default function AnalysisProgress({ symbols, onComplete, onError, autoStart = true }: AnalysisProgressProps) {
  const { locale } = useLocale();
  const initialSteps = useMemo<StepView[]>(
    () => STEP_ORDER.map((key) => ({ key, status: 'pending', elapsedMs: null })),
    []
  );

  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StepView[]>(initialSteps);
  const [currentMessage, setCurrentMessage] = useState('');
  const [summary, setSummary] = useState<Array<{ symbol: string; recommendationsCount: number }>>([]);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);

  const retriedRef = useRef(false);
  const startedRef = useRef(false);
  const stepStartRef = useRef<Partial<Record<StepKey, number>>>({});
  const resultsRef = useRef<AnalysisResult[]>([]);

  const resetState = useCallback(() => {
    setProgress(0);
    setSteps(initialSteps);
    setCurrentMessage('');
    setSummary([]);
    setError('');
    setRunning(false);
    stepStartRef.current = {};
    resultsRef.current = [];
  }, [initialSteps]);

  const updateByProgress = useCallback((payload: AnalysisStreamProgressEvent) => {
    const now = Date.now();
    const fallbackIndex = Math.max(0, Math.min(payload.step - 1, STEP_ORDER.length - 1));
    const stepIndex = normalizeStageToStepIndex(payload.stage, fallbackIndex);
    const stepKey = STEP_ORDER[stepIndex];
    stepStartRef.current[stepKey] = stepStartRef.current[stepKey] ?? now;

    setSteps((prev) => {
      const updated = nextStepsByIndex(prev, stepIndex, now);
      return updated.map((step, idx) => {
        if ((idx < stepIndex || idx === stepIndex) && step.elapsedMs === null) {
          const start = stepStartRef.current[step.key] ?? now;
          return { ...step, elapsedMs: Math.max(now - start, 0) };
        }
        return step;
      });
    });

    setProgress(payload.progress);
    setCurrentMessage(`${payload.symbol}: ${payload.stage} (${payload.step}/${payload.totalSteps})`);
  }, []);

  const updateByStep = useCallback((payload: AnalysisStreamStepEvent) => {
    const now = Date.now();
    const stepIndex = Math.max(0, Math.min(payload.currentStep - 1, STEP_ORDER.length - 1));
    setSteps((prev) => {
      const updated = nextStepsByIndex(prev, stepIndex, now);
      return updated.map((step, idx) => {
        if (idx <= stepIndex && step.elapsedMs === null) {
          const start = stepStartRef.current[step.key] ?? now;
          return { ...step, elapsedMs: Math.max(now - start, 0) };
        }
        return step;
      });
    });
  }, []);

  const runStream = useCallback(async () => {
    setRunning(true);
    setError('');

    try {
      await runAnalysisStream(symbols, {
        onStart: () => {
          setProgress(0);
          setCurrentMessage(getMessage(locale, 'interaction.status_running'));
          setSteps(initialSteps);
        },
        onProgress: (payload) => updateByProgress(payload),
        onStep: (payload) => updateByStep(payload),
        onResult: (payload) => {
          resultsRef.current = [...resultsRef.current, payload.result];
          setSummary((prev) => [
            ...prev,
            { symbol: payload.result.symbol, recommendationsCount: payload.result.recommendationsCount },
          ]);
          setProgress(payload.progress);
        },
        onDone: (payload) => {
          const now = Date.now();
          setSteps((prev) =>
            prev.map((step) => {
              const start = stepStartRef.current[step.key] ?? now;
              return { ...step, status: 'done', elapsedMs: step.elapsedMs ?? Math.max(now - start, 0) };
            })
          );
          setProgress(100);
          setCurrentMessage(getMessage(locale, 'interaction.status_done'));
          setRunning(false);
          onComplete({ results: resultsRef.current, totalTime: payload.totalTime, progress: payload.progress });
        },
      });
    } catch (streamError) {
      const message = streamError instanceof Error ? streamError.message : 'Analysis stream failed';
      if (!retriedRef.current) {
        retriedRef.current = true;
        setCurrentMessage(getMessage(locale, 'interaction.auto_retrying'));
        setTimeout(() => {
          void runStream();
        }, 250);
        return;
      }

      const now = Date.now();
      setRunning(false);
      setError(message);
      setSteps((prev) => {
        const activeIndex = prev.findIndex((step) => step.status === 'running');
        if (activeIndex < 0) return prev;
        return nextStepsByIndex(prev, activeIndex, now, true);
      });
      onError(message);
    }
  }, [symbols, locale, initialSteps, onComplete, onError, updateByProgress, updateByStep]);

  useEffect(() => {
    if (!autoStart || symbols.length === 0 || startedRef.current) return;
    startedRef.current = true;
    void runStream();
  }, [autoStart, symbols, runStream]);

  const handleRetry = async () => {
    retriedRef.current = false;
    resetState();
    await runStream();
  };

  return (
    <Paper elevation={0} className="card">
      <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 700, color: 'text.primary' }}>
        {getMessage(locale, 'interaction.progress_title')}
      </Typography>

      <div className="flex items-center justify-between text-sm">
        <span className="text-[var(--foreground)]">{currentMessage}</span>
        <span className="text-slate-500">{Math.round(progress)}%</span>
      </div>
      <LinearProgress variant="determinate" value={progress} sx={{ mt: 2, mb: 2, height: 10, borderRadius: 999, bgcolor: 'action.hover', '& .MuiLinearProgress-bar': { borderRadius: 999 } }} />

      <Stack spacing={1.5}>
        {steps.map((step) => (
          <div key={step.key} className="flex items-center justify-between rounded-2xl bg-[var(--card)]/30 px-3 py-2">
            <div className="flex items-center gap-2">
              <span aria-label={`status-${step.key}`}>{statusIcon(step.status)}</span>
              <span className="text-sm text-[var(--foreground)]">{getMessage(locale, STEP_LABEL_KEYS[step.key])}</span>
              <span className="text-xs text-slate-500">{getMessage(locale, STATUS_LABEL_KEYS[step.status])}</span>
            </div>
            <span className="text-xs text-slate-500">{getMessage(locale, 'interaction.elapsed_time')}: {formatElapsed(step.elapsedMs)}</span>
          </div>
        ))}
      </Stack>

      {summary.length > 0 && (
        <div className="mt-3 rounded-2xl bg-[var(--card)]/30 px-3 py-2">
          <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary' }}>
            {getMessage(locale, 'interaction.result_summary')}
          </Typography>
          <ul className="mt-1 space-y-1 text-xs text-slate-400">
            {summary.map((item) => (
              <li key={`${item.symbol}-${item.recommendationsCount}`}>{item.symbol}: {item.recommendationsCount}</li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <div className="mt-3 space-y-2">
          <Typography variant="body2" sx={{ color: 'error.main' }}>{error}</Typography>
          <Button onClick={handleRetry} disabled={running} variant="outlined" size="small">
            {getMessage(locale, 'interaction.retry_button')}
          </Button>
        </div>
      )}
    </Paper>
  );
}
