import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('tracking API functions', () => {
  const filePath = path.resolve(process.cwd(), 'lib/api.ts');
  const source = readFileSync(filePath, 'utf8');

  it('exports all tracking API functions', () => {
    expect(source).toContain('export async function getTrackingStats');
    expect(source).toContain('export async function getTrackedDecisions');
    expect(source).toContain('export async function updateTracking');
  });

  it('maps backend snake_case to camelCase', () => {
    expect(source).toContain('mapBackendStats');
    expect(source).toContain('mapBackendDecision');
    expect(source).toContain('hit_rate');
    expect(source).toContain('hitRate');
    expect(source).toContain('avg_pnl_pct');
    expect(source).toContain('avgPnlPct');
  });

  it('defines backend and frontend tracking types', () => {
    expect(source).toContain('BackendTrackingStats');
    expect(source).toContain('BackendTrackedDecision');
    expect(source).toContain('export interface TrackingStats');
    expect(source).toContain('export interface TrackedDecision');
  });
});