import type { Locale } from '../types';

export const backtestMessages: Record<Locale, { title: string; subtitle: string; }> = {
  'zh-CN': {
    title: '策略回测',
    subtitle: '模拟期权策略的历史表现',
  },
  en: {
    title: 'Strategy Backtest',
    subtitle: 'Simulate historical performance of options strategies',
  },
};
