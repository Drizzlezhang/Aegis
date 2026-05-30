'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Paper as MuiPaper, Snackbar, Tab, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Tabs, TextField,
  Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import {
  cancelPaperOrder, getPaperOrders, getPaperPortfolio, getPaperPositions,
  getSymbols, placePaperOrder, resetPaperTrading,
  type PaperOrder, type PaperPortfolio, type PaperPosition, type SymbolInfo,
} from '@/lib/api';

interface TabPanelProps {
  children: React.ReactNode;
  value: number;
  index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return value === index ? <Box sx={{ py: 2 }}>{children}</Box> : null;
}

export default function PaperPage() {
  const [tab, setTab] = useState(0);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [orders, setOrders] = useState<PaperOrder[]>([]);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null);
  const [loading, setLoading] = useState(true);

  // Order form
  const [orderSymbol, setOrderSymbol] = useState('');
  const [orderSide, setOrderSide] = useState('buy');
  const [orderType, setOrderType] = useState('market');
  const [orderQty, setOrderQty] = useState(10);
  const [orderLimit, setOrderLimit] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });

  // Reset dialog
  const [resetOpen, setResetOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [o, p, pf] = await Promise.all([
      getPaperOrders(),
      getPaperPositions(),
      getPaperPortfolio(),
    ]);
    setOrders(o.orders);
    setPositions(p.positions);
    setPortfolio(pf);
    setLoading(false);
  }, []);

  useEffect(() => {
    void getSymbols().then(setSymbols).catch(() => setSymbols([]));
    void fetchData();
  }, [fetchData]);

  const handlePlaceOrder = useCallback(async () => {
    if (!orderSymbol) return;
    const result = await placePaperOrder({
      symbol: orderSymbol.toUpperCase(),
      side: orderSide,
      orderType,
      quantity: orderQty,
      limitPrice: orderLimit ? parseFloat(orderLimit) : undefined,
    });
    if (result?.success) {
      setSnackbar({ open: true, message: `Order ${result.orderId} placed`, severity: 'success' });
      void fetchData();
    } else {
      setSnackbar({ open: true, message: 'Order failed', severity: 'error' });
    }
  }, [orderSymbol, orderSide, orderType, orderQty, orderLimit, fetchData]);

  const handleCancel = useCallback(async (orderId: string) => {
    const ok = await cancelPaperOrder(orderId);
    if (ok) {
      setSnackbar({ open: true, message: `Order ${orderId} cancelled`, severity: 'success' });
      void fetchData();
    }
  }, [fetchData]);

  const handleReset = useCallback(async () => {
    const ok = await resetPaperTrading();
    if (ok) {
      setSnackbar({ open: true, message: 'Paper trading state reset', severity: 'success' });
      setResetOpen(false);
      void fetchData();
    }
  }, [fetchData]);

  const statusColor = (status: string) => {
    switch (status) {
      case 'filled': return 'success';
      case 'pending': return 'warning';
      case 'cancelled': return 'default';
      case 'rejected': return 'error';
      default: return 'primary';
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="flex flex-1">
        <Sidebar symbols={symbols} />
        <main className="flex-1 p-4 lg:p-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-[var(--foreground)]">纸交易</h1>
                <p className="mt-2 text-sm text-slate-500">模拟交易环境，测试策略无需真实资金</p>
              </div>
              <Button variant="outlined" color="error" onClick={() => setResetOpen(true)}>
                重置
              </Button>
            </div>

            {/* Portfolio Summary */}
            {portfolio && (
              <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="card">
                  <div className="text-xs text-slate-500">现金</div>
                  <div className="mt-1 text-xl font-bold">${portfolio.cash.toLocaleString()}</div>
                </div>
                <div className="card">
                  <div className="text-xs text-slate-500">总权益</div>
                  <div className="mt-1 text-xl font-bold">${portfolio.equity.toLocaleString()}</div>
                </div>
                <div className="card">
                  <div className="text-xs text-slate-500">总盈亏</div>
                  <div className={`mt-1 text-xl font-bold ${portfolio.totalPnl >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                    ${portfolio.totalPnl.toFixed(2)} ({portfolio.totalPnlPct.toFixed(2)}%)
                  </div>
                </div>
                <div className="card">
                  <div className="text-xs text-slate-500">持仓数</div>
                  <div className="mt-1 text-xl font-bold">{portfolio.positionCount}</div>
                </div>
              </div>
            )}

            {/* Tabs */}
            <MuiPaper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '28px', mb: 3 }}>
              <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 2, pt: 1 }}>
                <Tab label="下单" />
                <Tab label={`订单 (${orders.length})`} />
                <Tab label={`持仓 (${positions.length})`} />
                <Tab label="投资组合" />
              </Tabs>
            </MuiPaper>

            {/* Tab 0: Place Order */}
            <TabPanel value={tab} index={0}>
              <div className="card max-w-md">
                <h2 className="mb-4 text-lg font-semibold">下单</h2>
                <div className="space-y-3">
                  <TextField label="标的" size="small" fullWidth value={orderSymbol}
                    onChange={(e) => setOrderSymbol(e.target.value.toUpperCase())}
                    placeholder="AAPL" />
                  <TextField label="方向" size="small" fullWidth select value={orderSide}
                    onChange={(e) => setOrderSide(e.target.value)}>
                    <option value="buy">买入</option>
                    <option value="sell">卖出</option>
                  </TextField>
                  <TextField label="类型" size="small" fullWidth select value={orderType}
                    onChange={(e) => setOrderType(e.target.value)}>
                    <option value="market">市价</option>
                    <option value="limit">限价</option>
                    <option value="stop">止损</option>
                  </TextField>
                  <TextField label="数量" size="small" fullWidth type="number" value={orderQty}
                    onChange={(e) => setOrderQty(parseInt(e.target.value) || 0)} />
                  {orderType !== 'market' && (
                    <TextField label="价格" size="small" fullWidth type="number" value={orderLimit}
                      onChange={(e) => setOrderLimit(e.target.value)} />
                  )}
                  <Button variant="contained" fullWidth onClick={handlePlaceOrder} disabled={!orderSymbol}>
                    下单
                  </Button>
                </div>
              </div>
            </TabPanel>

            {/* Tab 1: Orders */}
            <TabPanel value={tab} index={1}>
              {orders.length === 0 ? (
                <div className="card-muted text-center">
                  <p className="text-slate-500">暂无订单</p>
                </div>
              ) : (
                <TableContainer component={MuiPaper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>订单ID</TableCell>
                        <TableCell>标的</TableCell>
                        <TableCell>方向</TableCell>
                        <TableCell>类型</TableCell>
                        <TableCell>数量</TableCell>
                        <TableCell>状态</TableCell>
                        <TableCell>时间</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {orders.map((o) => (
                        <TableRow key={o.id}>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{o.id}</TableCell>
                          <TableCell>{o.symbol}</TableCell>
                          <TableCell>{o.side}</TableCell>
                          <TableCell>{o.orderType}</TableCell>
                          <TableCell>{o.filledQuantity}/{o.quantity}</TableCell>
                          <TableCell>
                            <Chip label={o.status} size="small" color={statusColor(o.status) as any} />
                          </TableCell>
                          <TableCell sx={{ fontSize: 12 }}>{new Date(o.createdAt).toLocaleString()}</TableCell>
                          <TableCell>
                            {(o.status === 'pending' || o.status === 'submitted') && (
                              <Button size="small" color="error" onClick={() => handleCancel(o.id)}>取消</Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </TabPanel>

            {/* Tab 2: Positions */}
            <TabPanel value={tab} index={2}>
              {positions.length === 0 ? (
                <div className="card-muted text-center">
                  <p className="text-slate-500">暂无持仓</p>
                </div>
              ) : (
                <TableContainer component={MuiPaper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>标的</TableCell>
                        <TableCell>数量</TableCell>
                        <TableCell>均价</TableCell>
                        <TableCell>市价</TableCell>
                        <TableCell>未实现盈亏</TableCell>
                        <TableCell>盈亏%</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {positions.map((p) => (
                        <TableRow key={p.symbol}>
                          <TableCell sx={{ fontWeight: 700 }}>{p.symbol}</TableCell>
                          <TableCell>{p.quantity}</TableCell>
                          <TableCell>${p.avgCost.toFixed(2)}</TableCell>
                          <TableCell>${(p.marketPrice ?? 0).toFixed(2)}</TableCell>
                          <TableCell>
                            <span className={(p.unrealizedPnl ?? 0) >= 0 ? 'text-red-500' : 'text-green-500'}>
                              ${(p.unrealizedPnl ?? 0).toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={(p.unrealizedPnlPct ?? 0) >= 0 ? 'text-red-500' : 'text-green-500'}>
                              {(p.unrealizedPnlPct ?? 0).toFixed(2)}%
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </TabPanel>

            {/* Tab 3: Portfolio */}
            <TabPanel value={tab} index={3}>
              {portfolio ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="card">
                    <h2 className="mb-3 text-lg font-semibold">账户概览</h2>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span className="text-slate-500">现金</span><span>${portfolio.cash.toLocaleString()}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">总权益</span><span>${portfolio.equity.toLocaleString()}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">购买力</span><span>${portfolio.buyingPower.toLocaleString()}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">总盈亏</span>
                        <span className={portfolio.totalPnl >= 0 ? 'text-red-500' : 'text-green-500'}>
                          ${portfolio.totalPnl.toFixed(2)} ({portfolio.totalPnlPct.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="card">
                    <h2 className="mb-3 text-lg font-semibold">权益曲线统计</h2>
                    {portfolio.equityCurveSnapshots > 0 ? (
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500">快照数</span><span>{portfolio.equityCurveSnapshots}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">总回报</span>
                          <span className={portfolio.totalReturnPct >= 0 ? 'text-red-500' : 'text-green-500'}>{portfolio.totalReturnPct.toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between"><span className="text-slate-500">最大回撤</span>
                          <span className="text-green-500">{portfolio.maxDrawdownPct.toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between"><span className="text-slate-500">最高权益</span><span>${portfolio.maxEquity.toLocaleString()}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500">最低权益</span><span>${portfolio.minEquity.toLocaleString()}</span></div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">暂无权益曲线数据</p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="card-muted text-center">
                  <p className="text-slate-500">无法加载投资组合数据</p>
                </div>
              )}
            </TabPanel>
          </div>
        </main>
      </div>

      {/* Reset Dialog */}
      <Dialog open={resetOpen} onClose={() => setResetOpen(false)}>
        <DialogTitle>确认重置</DialogTitle>
        <DialogContent>
          <Typography>这将清除所有订单、持仓和权益曲线数据。此操作不可撤销。</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetOpen(false)}>取消</Button>
          <Button onClick={handleReset} color="error" variant="contained">确认重置</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setSnackbar((p) => ({ ...p, open: false }))} severity={snackbar.severity} variant="filled" sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
}
