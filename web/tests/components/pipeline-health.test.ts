import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('pipeline health component source checks', () => {
  const filePath = path.resolve(process.cwd(), 'components/PipelineHealth.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('keeps six hardcoded pipeline agents', () => {
    expect(source).toContain("'Data-Harvester'");
    expect(source).toContain("'Quant-Brain'");
    expect(source).toContain("'Investment-Debate'");
    expect(source).toContain("'Strategy-Execution'");
    expect(source).toContain("'Aegis-Memory'");
    expect(source).toContain("'Position-Monitor'");
  });

  it('renders pipeline summary metrics', () => {
    expect(source).toContain('pipeline.total_runs');
    expect(source).toContain('pipeline.last_run_time');
    expect(source).toContain('pipeline.avg_duration_seconds');
  });

  it('renders llm metrics', () => {
    expect(source).toContain('pipeline.llm.requests');
    expect(source).toContain('pipeline.llm.tokens');
    expect(source).toContain('pipeline.llm.errors');
  });

  it('keeps no-data fallback', () => {
    expect(source).toContain('if (!pipeline)');
    expect(source).toContain("getMessage(locale, 'interaction.pipeline_no_data')");
  });
});
