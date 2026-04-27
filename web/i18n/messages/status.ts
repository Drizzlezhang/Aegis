import type { Locale } from '../types';

export const statusMessages: Record<Locale, { title: string; subtitle: string; }> = {
  'zh-CN': {
    title: '系统状态',
    subtitle: 'Agent 健康状态、Skills 与系统指标',
  },
  en: {
    title: 'System Status',
    subtitle: 'Agent health, skills, and system metrics',
  },
};
