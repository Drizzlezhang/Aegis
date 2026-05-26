'use client';

import { Fragment, useMemo, useState } from 'react';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import KeyboardArrowUpRoundedIcon from '@mui/icons-material/KeyboardArrowUpRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import {
  Box,
  Chip,
  Collapse,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { getMessage } from '@/i18n/get-message';
import { getChangeColorClasses } from '@/lib/change-color';
import { getPositionChain, type PositionChainItem, type PositionData, type PositionSummaryData } from '@/lib/api';
import { useLocale } from './LocaleProvider';

interface PositionTableProps {
  positions: PositionData[];
  summary: PositionSummaryData | null;
  onClose?: (position: PositionData) => void;
  onRoll?: (position: PositionData) => void;
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return '--';
  }
  return `$${value.toFixed(2)}`;
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return '--';
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatDate(value: string | null): string {
  if (!value) {
    return '--';
  }
  return value;
}

export default function PositionTable({ positions, summary, onClose, onRoll }: PositionTableProps) {
  const { locale } = useLocale();
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
  const [chainLoadingMap, setChainLoadingMap] = useState<Record<string, boolean>>({});
  const [chainsMap, setChainsMap] = useState<Record<string, PositionChainItem[]>>({});

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aRank = a.status === 'active' ? 0 : 1;
      const bRank = b.status === 'active' ? 0 : 1;
      if (aRank !== bRank) {
        return aRank - bRank;
      }
      return a.symbol.localeCompare(b.symbol);
    });
  }, [positions]);

  const toggleRow = async (positionId: string) => {
    const nextExpanded = !expandedMap[positionId];
    setExpandedMap((prev) => ({ ...prev, [positionId]: nextExpanded }));

    if (!nextExpanded || chainsMap[positionId] || chainLoadingMap[positionId]) {
      return;
    }

    setChainLoadingMap((prev) => ({ ...prev, [positionId]: true }));
    try {
      const chain = await getPositionChain(positionId);
      setChainsMap((prev) => ({ ...prev, [positionId]: chain }));
    } catch {
      setChainsMap((prev) => ({ ...prev, [positionId]: [] }));
    } finally {
      setChainLoadingMap((prev) => ({ ...prev, [positionId]: false }));
    }
  };

  return (
    <Paper elevation={0} className="card">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'text.primary' }}>
          {getMessage(locale, 'interaction.positions_title')}
        </Typography>
        <Chip label={String(summary?.total_positions ?? positions.length)} size="small" variant="outlined" />
      </div>

      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
        {getMessage(locale, 'interaction.positions_subtitle')}
      </Typography>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatItem label={getMessage(locale, 'interaction.positions_total_positions')} value={String(summary?.total_positions ?? 0)} />
        <StatItem label={getMessage(locale, 'interaction.positions_active_count')} value={String(summary?.active_count ?? 0)} />
        <StatItem label={getMessage(locale, 'interaction.positions_closed_count')} value={String(summary?.closed_count ?? 0)} />
        <StatItem label={getMessage(locale, 'interaction.positions_realized_pnl')} value={formatCurrency(summary?.total_realized_pnl ?? 0)} />
        <StatItem label={getMessage(locale, 'interaction.positions_unrealized_pnl')} value={formatCurrency(summary?.total_unrealized_pnl ?? 0)} />
      </div>

      {sortedPositions.length === 0 ? (
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {getMessage(locale, 'interaction.positions_empty')}
        </Typography>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width={48} />
                <TableCell>{getMessage(locale, 'interaction.positions_symbol')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_status')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_strike')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_expiry')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_dte')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_entry_price')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_current_price')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_pnl')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_pnl_pct')}</TableCell>
                <TableCell>{getMessage(locale, 'interaction.positions_quantity')}</TableCell>
                {(onClose || onRoll) && <TableCell width={96} />}
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedPositions.map((position) => {
                const expanded = Boolean(expandedMap[position.id]);
                const pnlUp = (position.pnl ?? 0) >= 0;
                const pnlClass = getChangeColorClasses(pnlUp).text;
                const pnlPctUp = (position.pnl_pct ?? 0) >= 0;
                const pnlPctClass = getChangeColorClasses(pnlPctUp).text;

                let dteColor: 'default' | 'warning' | 'error' = 'default';
                if (position.dte <= 30) {
                  dteColor = 'error';
                } else if (position.dte <= 60) {
                  dteColor = 'warning';
                }

                return (
                  <Fragment key={position.id}>
                    <TableRow hover>
                      <TableCell>
                        <IconButton size="small" onClick={() => void toggleRow(position.id)}>
                          {expanded ? <KeyboardArrowUpRoundedIcon fontSize="small" /> : <KeyboardArrowDownRoundedIcon fontSize="small" />}
                        </IconButton>
                      </TableCell>
                      <TableCell>{position.symbol}</TableCell>
                      <TableCell>
                        <Chip label={position.status} size="small" variant={position.status === 'active' ? 'filled' : 'outlined'} color={position.status === 'active' ? 'primary' : 'default'} />
                      </TableCell>
                      <TableCell>{position.strike.toFixed(2)}</TableCell>
                      <TableCell>{position.expiry}</TableCell>
                      <TableCell>
                        <Chip label={`${position.dte}`} size="small" color={dteColor} variant={dteColor === 'default' ? 'outlined' : 'filled'} />
                      </TableCell>
                      <TableCell>{formatCurrency(position.entry_price)}</TableCell>
                      <TableCell>{formatCurrency(position.current_price)}</TableCell>
                      <TableCell>
                        <span className={position.pnl === null ? '' : pnlClass}>{formatCurrency(position.pnl)}</span>
                      </TableCell>
                      <TableCell>
                        <span className={position.pnl_pct === null ? '' : pnlPctClass}>{formatPercent(position.pnl_pct)}</span>
                      </TableCell>
                      <TableCell>{position.quantity}</TableCell>
                      {(onClose || onRoll) && (
                        <TableCell>
                          {position.status === 'active' && (
                            <Stack direction="row" spacing={0.5}>
                              {onRoll && (
                                <Tooltip title="Roll">
                                  <IconButton size="small" color="primary" onClick={() => onRoll(position)}>
                                    <AutorenewRoundedIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                              {onClose && (
                                <Tooltip title="Close">
                                  <IconButton size="small" color="error" onClick={() => onClose(position)}>
                                    <CloseRoundedIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                            </Stack>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                    <TableRow>
                      <TableCell colSpan={onClose || onRoll ? 12 : 11} sx={{ py: 0, borderBottom: 'none' }}>
                        <Collapse in={expanded} timeout="auto" unmountOnExit>
                          <Box sx={{ p: 2 }}>
                            {chainLoadingMap[position.id] ? (
                              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                {getMessage(locale, 'interaction.positions_loading_chain')}
                              </Typography>
                            ) : (
                              <ChainSection chain={chainsMap[position.id] ?? []} />
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}

function ChainSection({ chain }: { chain: PositionChainItem[] }) {
  const { locale } = useLocale();

  if (chain.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
        {getMessage(locale, 'interaction.positions_chain_empty')}
      </Typography>
    );
  }

  return (
    <Stack spacing={1.5}>
      {chain.map((item) => (
        <Paper key={item.id} elevation={0} className="card-muted">
          <div className="flex flex-wrap items-center gap-2">
            <Chip label={item.status} size="small" variant="outlined" />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {getMessage(locale, 'interaction.positions_entry_date')}: {formatDate(item.entry_date)}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {getMessage(locale, 'interaction.positions_close_date')}: {formatDate(item.close_date)}
            </Typography>
          </div>

          {item.actions.length === 0 ? (
            <Typography variant="caption" sx={{ mt: 1, display: 'block', color: 'text.secondary' }}>
              {getMessage(locale, 'interaction.positions_no_actions')}
            </Typography>
          ) : (
            <Stack spacing={0.5} sx={{ mt: 1.5 }}>
              {item.actions.map((action) => (
                <Typography key={`${item.id}-${action.action_type}-${action.date}-${action.price}`} variant="caption" sx={{ color: 'text.secondary' }}>
                  {action.action_type} · {action.date} · ${action.price.toFixed(2)} · x{action.quantity}
                  {action.notes ? ` · ${action.notes}` : ''}
                </Typography>
              ))}
            </Stack>
          )}
        </Paper>
      ))}
    </Stack>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <Paper elevation={0} className="card-muted">
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 700, color: 'text.primary' }}>
        {value}
      </Typography>
    </Paper>
  );
}
