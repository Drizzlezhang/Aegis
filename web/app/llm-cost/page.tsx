'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Box, Chip, Paper as MuiPaper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, ToggleButton, ToggleButtonGroup,
  Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import {
  getLlmBudget, getLlmCacheStats, getLlmCost, getSymbols,
  type LlmBudgetStatus, type LlmCacheStats, type LlmCostBreakdown, type SymbolInfo,
} from '@/lib/api';

export default function LlmCostPage() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [period, setPeriod] = useState('7d');
  const [groupBy, setGroupBy] = useState('agent');
  const [breakdown, setBreakdown] = useState<LlmCostBreakdown[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [budget, setBudget] = useState<LlmBudgetStatus | null>(null);
  const [cache, setCache] = useState<LlmCacheStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [costData, budgetData, cacheData] = await Promise.all([
      getLlmCost(period, groupBy),
      getLlmBudget(),
      getLlmCacheStats(),
    ]);
    if (costData) {
      setBreakdown(costData.breakdown);
      setTotalCost(costData.totalCost);
      setTotalTokens(costData.totalTokens);
    }
    setBudget(budgetData);
    setCache(cacheData);
    setLoading(false);
  }, [period, groupBy]);

  useEffect(() => {
    void getSymbols().then(setSymbols).catch(() => setSymbols([]));
    void fetchData();
  }, [fetchData]);

  const budgetStatusColor = (status: string) => {
    switch (status) {
      case 'ok': return 'success';
      case 'warning': return 'warning';
      case 'critical': return 'error';
      default: return 'default';
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-[var(--foreground)]">LLM 成本</h1>
              <p className="mt-2 text-sm text-slate-500">LLM 调用成本治理与预算监控</p>
            </div>

            {/* KPI Cards */}
            <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="card">
                <div className="text-xs text-slate-500">总成本 ({period})</div>
                <div className="mt-1 text-xl font-bold">${totalCost.toFixed(4)}</div>
              </div>
              <div className="card">
                <div className="text-xs text-slate-500">总 Token</div>
                <div className="mt-1 text-xl font-bold">{totalTokens.toLocaleString()}</div>
              </div>
              {cache && (
                <div className="card">
                  <div className="text-xs text-slate-500">缓存命中率</div>
                  <div className="mt-1 text-xl font-bold">{(cache.hitRate * 100).toFixed(1)}%</div>
                  <div className="mt-1 text-xs text-slate-500">预估节省 ${cache.estimatedSavings.toFixed(4)}</div>
                </div>
              )}
              {budget && (
                <div className="card">
                  <div className="text-xs text-slate-500">月度预算</div>
                  <div className="mt-1 text-xl font-bold">
                    ${budget.monthly.usedUsd.toFixed(4)}
                    <span className="text-sm font-normal text-slate-500"> / ${budget.monthly.limitUsd.toFixed(2)}</span>
                  </div>
                  <Chip
                    label={`${budget.monthly.pct.toFixed(1)}%`}
                    size="small"
                    color={budgetStatusColor(budget.monthly.status) as any}
                    sx={{ mt: 0.5 }}
                  />
                </div>
              )}
            </div>

            {/* Budget Details */}
            {budget && (
              <div className="mb-6 grid gap-4 md:grid-cols-2">
                <div className="card">
                  <h2 className="mb-3 text-lg font-semibold">日预算</h2>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">状态</span>
                      <Chip label={budget.daily.status.toUpperCase()} size="small"
                        color={budgetStatusColor(budget.daily.status) as any} />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">限额</span><span>${budget.daily.limitUsd.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">已用</span><span>${budget.daily.usedUsd.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">剩余</span><span>${budget.daily.remainingUsd.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">使用率</span><span>{budget.daily.pct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <h2 className="mb-3 text-lg font-semibold">月预算</h2>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">状态</span>
                      <Chip label={budget.monthly.status.toUpperCase()} size="small"
                        color={budgetStatusColor(budget.monthly.status) as any} />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">限额</span><span>${budget.monthly.limitUsd.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">已用</span><span>${budget.monthly.usedUsd.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">剩余</span><span>${budget.monthly.remainingUsd.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">使用率</span><span>{budget.monthly.pct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Cost Breakdown */}
            <div className="mb-6">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold">成本明细</h2>
                <div className="flex gap-2">
                  <ToggleButtonGroup size="small" value={period} exclusive onChange={(_, v) => v && setPeriod(v)}>
                    <ToggleButton value="today">今日</ToggleButton>
                    <ToggleButton value="7d">7天</ToggleButton>
                    <ToggleButton value="30d">30天</ToggleButton>
                  </ToggleButtonGroup>
                  <ToggleButtonGroup size="small" value={groupBy} exclusive onChange={(_, v) => v && setGroupBy(v)}>
                    <ToggleButton value="agent">按Agent</ToggleButton>
                    <ToggleButton value="model">按模型</ToggleButton>
                    <ToggleButton value="day">按天</ToggleButton>
                  </ToggleButtonGroup>
                </div>
              </div>

              {breakdown.length === 0 ? (
                <div className="card-muted text-center">
                  <p className="text-slate-500">暂无数据</p>
                </div>
              ) : (
                <TableContainer component={MuiPaper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{groupBy === 'agent' ? 'Agent' : groupBy === 'model' ? '模型' : '日期'}</TableCell>
                        <TableCell align="right">输入 Token</TableCell>
                        <TableCell align="right">输出 Token</TableCell>
                        <TableCell align="right">成本</TableCell>
                        <TableCell align="right">调用次数</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {breakdown.map((item) => (
                        <TableRow key={item.key}>
                          <TableCell sx={{ fontWeight: 600 }}>{item.key}</TableCell>
                          <TableCell align="right">{item.inputTokens.toLocaleString()}</TableCell>
                          <TableCell align="right">{item.outputTokens.toLocaleString()}</TableCell>
                          <TableCell align="right" sx={{ fontFamily: 'monospace' }}>
                            ${item.cost.toFixed(4)}
                          </TableCell>
                          <TableCell align="right">{item.calls}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </div>

            {/* Cache Stats */}
            {cache && (
              <div className="card">
                <h2 className="mb-3 text-lg font-semibold">缓存统计</h2>
                <div className="grid gap-4 sm:grid-cols-4">
                  <div>
                    <div className="text-xs text-slate-500">命中</div>
                    <div className="text-lg font-bold">{cache.hits}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">未命中</div>
                    <div className="text-lg font-bold">{cache.misses}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">命中率</div>
                    <div className="text-lg font-bold">{(cache.hitRate * 100).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">预估节省</div>
                    <div className="text-lg font-bold">${cache.estimatedSavings.toFixed(4)}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
