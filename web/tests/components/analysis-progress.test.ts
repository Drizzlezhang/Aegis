import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('analysis progress component', () => {
  const filePath = path.resolve(process.cwd(), 'components/AnalysisProgress.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('defines four pipeline steps', () => {
    expect(source).toContain("const STEP_ORDER: StepKey[] = ['data_harvester', 'quant_brain', 'strategy', 'memory']");
  });

  it('wires SSE event handlers', () => {
    expect(source).toContain('onStart: () =>');
    expect(source).toContain('onProgress: (payload) =>');
    expect(source).toContain('onStep: (payload) =>');
    expect(source).toContain('onResult: (payload) =>');
    expect(source).toContain('onDone: (payload) =>');
    expect(source).toContain("'Analysis stream failed'");
  });

  it('supports auto reconnect once and manual retry', () => {
    expect(source).toContain('const retriedRef = useRef(false)');
    expect(source).toContain('if (!retriedRef.current)');
    expect(source).toContain('setTimeout(() =>');
    expect(source).toContain('const handleRetry = async () =>');
    expect(source).toContain("getMessage(locale, 'interaction.retry_button')");
  });

  it('uses i18n keys for step labels and statuses', () => {
    expect(source).toContain("'interaction.step_data_harvester'");
    expect(source).toContain("'interaction.step_quant_brain'");
    expect(source).toContain("'interaction.step_strategy'");
    expect(source).toContain("'interaction.step_memory'");
    expect(source).toContain("'interaction.status_pending'");
    expect(source).toContain("'interaction.status_running'");
    expect(source).toContain("'interaction.status_done'");
    expect(source).toContain("'interaction.status_error'");
  });
});
