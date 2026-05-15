import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('analysis progress component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/AnalysisProgress.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('keeps four pipeline steps', () => {
    expect(source).toContain("const STEP_ORDER: StepKey[] = ['data_harvester', 'quant_brain', 'strategy', 'memory']");
  });

  it('passes AbortSignal and cleans up on unmount', () => {
    expect(source).toContain('const controller = new AbortController()');
    expect(source).toContain('void runStream(controller.signal)');
    expect(source).toContain('return () => controller.abort()');
    expect(source).toContain('const runStream = useCallback(async (signal?: AbortSignal) =>');
    expect(source).toContain('if (signal?.aborted)');
  });

  it('keeps retry flow with manual retry button', () => {
    expect(source).toContain('if (!retriedRef.current)');
    expect(source).toContain('setTimeout(() =>');
    expect(source).toContain('const handleRetry = () =>');
    expect(source).toContain("getMessage(locale, 'interaction.retry_button')");
  });
});
