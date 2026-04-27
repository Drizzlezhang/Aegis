import type { Locale } from '../types';

export const historyMessages: Record<Locale, { title: string; subtitle: string; }> = {
  'zh-CN': {
    title: '分析历史',
    subtitle: '最近的多 Agent 分析执行记录',
  },
  en: {
    title: 'Analysis History',
    subtitle: 'Recent multi-agent analysis executions',
  },
};
