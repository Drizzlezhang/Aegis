'use client';

import React, { useState, useCallback } from 'react';
import {
  Box, Accordion, AccordionSummary, AccordionDetails,
  Typography, Button, Stack, LinearProgress, IconButton, Tooltip
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ShareIcon from '@mui/icons-material/Share';
import { getMessage } from '@/i18n/get-message';
import type { Locale } from '@/i18n/types';

interface ReportSection {
  id: string;
  title: string;
  content: string;
}

interface StructuredReport {
  sections: ReportSection[];
  metadata?: {
    language?: string;
    section_count?: number;
    debate_verdict?: string;
    bull_confidence?: number;
    bear_confidence?: number;
  };
}

interface AnalysisReportProps {
  report: StructuredReport;
  defaultExpanded?: string[];
  locale?: Locale;
}

export function AnalysisReport({ report, defaultExpanded, locale = 'zh-CN' }: AnalysisReportProps) {
  const initialExpanded = defaultExpanded || ['executive_summary'];
  const [expanded, setExpanded] = useState<Set<string>>(new Set(initialExpanded));

  const toggleSection = useCallback((id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpanded(new Set(report.sections.map(s => s.id)));
  }, [report]);

  const collapseAll = useCallback(() => {
    setExpanded(new Set());
  }, []);

  const handleShare = useCallback(async () => {
    const text = report.sections.map(s => `## ${s.title}\n\n${s.content}`).join('\n\n---\n\n');
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback: silent fail
    }
  }, [report]);

  const highlightNumbers = (text: string): React.ReactNode => {
    const parts = text.split(/(\$[\d,.]+|\d+\.?\d*%)/g);
    return parts.map((part, i) => {
      if (part.startsWith('$')) {
        return <span key={i} style={{ fontWeight: 'bold', color: '#1976d2' }}>{part}</span>;
      }
      if (part.endsWith('%')) {
        const num = parseFloat(part);
        const color = num > 0 ? '#d32f2f' : num < 0 ? '#2e7d32' : undefined;
        return <span key={i} style={{ fontWeight: 'bold', color }}>{part}</span>;
      }
      return part;
    });
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={expandAll}>{getMessage(locale, 'interaction.reportExpandAll')}</Button>
          <Button size="small" onClick={collapseAll}>{getMessage(locale, 'interaction.reportCollapseAll')}</Button>
        </Stack>
        <Tooltip title={getMessage(locale, 'interaction.reportShare')}>
          <IconButton size="small" onClick={handleShare}>
            <ShareIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      {report.sections.map(section => (
        <Accordion
          key={section.id}
          expanded={expanded.has(section.id)}
          onChange={() => toggleSection(section.id)}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography fontWeight="bold">{section.title}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {section.id === 'debate_summary' && report.metadata?.bull_confidence != null ? (
              <Box sx={{ mb: 2 }}>
                <Stack spacing={1}>
                  <Box>
                    <Typography variant="caption">Bull: {(report.metadata.bull_confidence * 100).toFixed(0)}%</Typography>
                    <LinearProgress
                      variant="determinate"
                      value={report.metadata.bull_confidence * 100}
                      color="error"
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                  <Box>
                    <Typography variant="caption">Bear: {((report.metadata.bear_confidence || 0) * 100).toFixed(0)}%</Typography>
                    <LinearProgress
                      variant="determinate"
                      value={(report.metadata.bear_confidence || 0) * 100}
                      color="success"
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                </Stack>
              </Box>
            ) : null}
            <Typography variant="body2" component="div" sx={{ whiteSpace: 'pre-wrap' }}>
              {highlightNumbers(section.content)}
            </Typography>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
