'use client';

import {
  Chip,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import { getMessage } from '@/i18n/get-message';
import { getChangeColorClasses } from '@/lib/change-color';
import { useLocale } from '@/components/LocaleProvider';
import type { BacktestRunSummary } from '@/lib/api';

interface BacktestHistoryTableProps {
  runs: BacktestRunSummary[];
  onSelect: (runId: string) => void;
  onDelete: (runId: string) => void;
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) return '--';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '--';
  return value.slice(0, 10);
}

function formatDateRange(startDate: string, endDate: string): string {
  return `${formatDate(startDate)} ~ ${formatDate(endDate)}`;
}

export default function BacktestHistoryTable({ runs, onSelect, onDelete }: BacktestHistoryTableProps) {
  const { locale } = useLocale();

  if (runs.length === 0) {
    return (
      <Paper elevation={0} className="card p-8 text-center">
        <Typography color="text.secondary">
          {getMessage(locale, 'backtestHistoryPage.noHistory')}
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper} elevation={0} className="card">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{getMessage(locale, 'backtestHistoryPage.symbol')}</TableCell>
            <TableCell>{getMessage(locale, 'backtestHistoryPage.strategy')}</TableCell>
            <TableCell>{getMessage(locale, 'backtestHistoryPage.dateRange')}</TableCell>
            <TableCell align="right">{getMessage(locale, 'backtestHistoryPage.return')}</TableCell>
            <TableCell align="right">{getMessage(locale, 'backtestHistoryPage.maxDrawdown')}</TableCell>
            <TableCell align="right">{getMessage(locale, 'backtestHistoryPage.trades')}</TableCell>
            <TableCell>{getMessage(locale, 'backtestHistoryPage.createdAt')}</TableCell>
            <TableCell align="center" sx={{ width: 120 }} />
          </TableRow>
        </TableHead>
        <TableBody>
          {runs.map((run) => {
            const isPositive = run.totalReturn >= 0;
            const colors = getChangeColorClasses(isPositive);

            return (
              <TableRow key={run.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>
                    {run.symbol}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={run.strategy}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.75rem' }}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {formatDateRange(run.startDate, run.endDate)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" className={colors.text} fontWeight={600}>
                    {formatPercent(run.totalReturn)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" color="text.secondary">
                    {formatPercent(run.maxDrawdown)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2">{run.totalTrades}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {formatDate(run.createdAt)}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title={getMessage(locale, 'backtestHistoryPage.view')}>
                    <IconButton size="small" onClick={() => onSelect(run.id)}>
                      <VisibilityRoundedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={getMessage(locale, 'backtestHistoryPage.delete')}>
                    <IconButton size="small" onClick={() => onDelete(run.id)}>
                      <DeleteRoundedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
