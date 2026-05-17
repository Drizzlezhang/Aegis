import type { ComponentProps } from 'react';
import type { AnalysisReport } from '@/components/AnalysisReport';

type StructuredReport = ComponentProps<typeof AnalysisReport>['report'];

export function isStructuredReport(value: unknown): value is StructuredReport {
  return Boolean(
    value
    && typeof value === 'object'
    && 'sections' in value
    && Array.isArray((value as { sections?: unknown }).sections)
  );
}
