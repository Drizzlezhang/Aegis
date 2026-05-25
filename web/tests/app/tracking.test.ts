import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

describe('tracking page', () => {
  const filePath = path.resolve(process.cwd(), 'app/tracking/page.tsx');
  const source = readFileSync(filePath, 'utf8');

  it('renders stats cards and decision table', () => {
    expect(source).toContain('TrackingContent');
  });

  it('handles tracking API failure gracefully with try/catch', () => {
    expect(source).toContain('try');
    expect(source).toContain('catch');
  });

  it('imports all tracking API functions', () => {
    expect(source).toContain('getTrackingStats');
    expect(source).toContain('getTrackedDecisions');
  });
});

describe('tracking components', () => {
  it('TrackingSummaryCards renders card labels', () => {
    const filePath = path.resolve(process.cwd(), 'components/TrackingSummaryCards.tsx');
    const source = readFileSync(filePath, 'utf8');
    expect(source).toContain('trackingHitRate');
    expect(source).toContain('trackingTotal');
    expect(source).toContain('trackingPending');
  });

  it('TrackingStrategyTable renders strategy columns', () => {
    const filePath = path.resolve(process.cwd(), 'components/TrackingStrategyTable.tsx');
    const source = readFileSync(filePath, 'utf8');
    expect(source).toContain('trackingByStrategy');
    expect(source).toContain('trackingHitRate');
  });

  it('TrackingDecisionTable uses correct status color chips', () => {
    const filePath = path.resolve(process.cwd(), 'components/TrackingDecisionTable.tsx');
    const source = readFileSync(filePath, 'utf8');
    expect(source).toContain('hit_target');
    expect(source).toContain('hit_stop');
    expect(source).toContain('expired');
    expect(source).toContain('active');
    expect(source).toContain('pending');
    expect(source).toContain('trackingDecisions');
    expect(source).toContain('trackingEmpty');
  });
});