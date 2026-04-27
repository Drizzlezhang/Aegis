import type { Locale } from '../types';

export const homeMessages: Record<Locale, { title: string; subtitle: string; marketIndices: string; systemStatus: string; agents: string; skills: string; lastUpdate: string; lastUpdateValue: string; active: string; loaded: string; }> = {
  'zh-CN': {
    title: '仪表盘',
    subtitle: '多 Agent 量化分析总览',
    marketIndices: '市场指数',
    systemStatus: '系统状态',
    agents: 'Agents',
    skills: 'Skills',
    lastUpdate: '最近更新',
    lastUpdateValue: '刚刚',
    active: '活跃',
    loaded: '已加载',
  },
  en: {
    title: 'Dashboard',
    subtitle: 'Multi-Agent quantitative analysis overview',
    marketIndices: 'Market Indices',
    systemStatus: 'System Status',
    agents: 'Agents',
    skills: 'Skills',
    lastUpdate: 'Last update',
    lastUpdateValue: 'just now',
    active: 'active',
    loaded: 'loaded',
  },
};
