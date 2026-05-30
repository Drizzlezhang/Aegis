'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Badge, Box, Button, Chip, Paper as MuiPaper, Tab, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Tabs, Typography,
} from '@mui/material';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import {
  getNotifications, getPositionAlerts, getSymbols,
  markAllNotificationsRead, markNotificationRead,
  type NotificationItem, type SymbolInfo,
} from '@/lib/api';

interface AlertItem {
  type: string;
  positionId: string;
  symbol: string;
  message: string;
  severity: string;
  suggestedAction: string;
}

export default function AlertsPage() {
  const [tab, setTab] = useState(0);
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [positionAlerts, setPositionAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [notifData, posData] = await Promise.all([
        getNotifications(50),
        getPositionAlerts(),
      ]);
      setNotifications(notifData.notifications);
      setUnreadCount(notifData.unreadCount);
      setPositionAlerts(posData.alerts ?? []);
    } catch {
      // graceful degradation
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void getSymbols().then(setSymbols).catch(() => setSymbols([]));
    void fetchData();
  }, [fetchData]);

  const handleMarkRead = useCallback(async (id: string) => {
    await markNotificationRead(id);
    void fetchData();
  }, [fetchData]);

  const handleMarkAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    void fetchData();
  }, [fetchData]);

  const severityColor = (s: string) => {
    switch (s) {
      case 'critical': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'default';
    }
  };

  const levelColor = (level: string) => {
    switch (level) {
      case 'critical': case 'error': return 'error';
      case 'warning': return 'warning';
      default: return 'info';
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
                <h1 className="text-3xl font-bold text-[var(--foreground)]">告警中心</h1>
                <p className="mt-2 text-sm text-slate-500">系统通知与持仓告警</p>
              </div>
              {unreadCount > 0 && (
                <Button variant="outlined" size="small" onClick={handleMarkAllRead}>
                  全部已读
                </Button>
              )}
            </div>

            <MuiPaper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '28px', mb: 3 }}>
              <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 2, pt: 1 }}>
                <Tab label={
                  <Badge badgeContent={unreadCount} color="error">
                    <span>通知</span>
                  </Badge>
                } />
                <Tab label={`持仓告警 (${positionAlerts.length})`} />
              </Tabs>
            </MuiPaper>

            {/* Tab 0: Notifications */}
            {tab === 0 && (
              notifications.length === 0 ? (
                <div className="card-muted text-center">
                  <p className="text-slate-500">暂无通知</p>
                </div>
              ) : (
                <TableContainer component={MuiPaper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>级别</TableCell>
                        <TableCell>类别</TableCell>
                        <TableCell>标题</TableCell>
                        <TableCell>消息</TableCell>
                        <TableCell>时间</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {notifications.map((n) => (
                        <TableRow key={n.id} sx={{ bgcolor: n.read ? 'transparent' : 'action.hover' }}>
                          <TableCell>
                            <Chip label={n.level} size="small" color={levelColor(n.level) as any} />
                          </TableCell>
                          <TableCell>
                            <Chip label={n.category} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell sx={{ fontWeight: n.read ? 400 : 700 }}>{n.title}</TableCell>
                          <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {n.message}
                          </TableCell>
                          <TableCell sx={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                            {new Date(n.createdAt).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            {!n.read && (
                              <Button size="small" onClick={() => handleMarkRead(n.id)}>已读</Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )
            )}

            {/* Tab 1: Position Alerts */}
            {tab === 1 && (
              positionAlerts.length === 0 ? (
                <div className="card-muted text-center">
                  <p className="text-slate-500">暂无持仓告警</p>
                </div>
              ) : (
                <TableContainer component={MuiPaper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '16px' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>类型</TableCell>
                        <TableCell>标的</TableCell>
                        <TableCell>严重度</TableCell>
                        <TableCell>消息</TableCell>
                        <TableCell>建议操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {positionAlerts.map((a, i) => (
                        <TableRow key={`${a.positionId}-${i}`}>
                          <TableCell>
                            <Chip label={a.type} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>{a.symbol}</TableCell>
                          <TableCell>
                            <Chip label={a.severity} size="small" color={severityColor(a.severity) as any} />
                          </TableCell>
                          <TableCell>{a.message}</TableCell>
                          <TableCell>{a.suggestedAction || '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
