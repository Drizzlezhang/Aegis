import type { Locale } from '../types';

export const backtestHistoryMessages: Record<Locale, {
  title: string;
  subtitle: string;
  noHistory: string;
  filterSymbol: string;
  view: string;
  delete: string;
  deleteConfirm: string;
  symbol: string;
  strategy: string;
  dateRange: string;
  return: string;
  maxDrawdown: string;
  trades: string;
  createdAt: string;
}> = {
  'zh-CN': {
    title: '回测历史',
    subtitle: '查看和管理历史回测记录',
    noHistory: '暂无回测历史',
    filterSymbol: '按标的筛选',
    view: '查看',
    delete: '删除',
    deleteConfirm: '确定要删除这条回测记录吗？',
    symbol: '标的',
    strategy: '策略',
    dateRange: '日期范围',
    return: '收益',
    maxDrawdown: '最大回撤',
    trades: '交易次数',
    createdAt: '创建时间',
  },
  en: {
    title: 'Backtest History',
    subtitle: 'View and manage historical backtest records',
    noHistory: 'No backtest history',
    filterSymbol: 'Filter by symbol',
    view: 'View',
    delete: 'Delete',
    deleteConfirm: 'Are you sure you want to delete this backtest record?',
    symbol: 'Symbol',
    strategy: 'Strategy',
    dateRange: 'Date Range',
    return: 'Return',
    maxDrawdown: 'Max Drawdown',
    trades: 'Trades',
    createdAt: 'Created',
  },
};
