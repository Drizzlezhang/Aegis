import type { Locale } from '../types';

export const marketMessages: Record<Locale, { title: string; subtitle: string; error: string; marketSentiment: string; vixLevel: string; positionSizing: string; noData: string; }> = {
  'zh-CN': {
    title: '市场概览',
    subtitle: '实时市场指数与情绪概览',
    error: '错误',
    marketSentiment: '市场情绪',
    vixLevel: 'VIX 水平',
    positionSizing: '仓位建议',
    noData: '暂无市场数据。',
  },
  en: {
    title: 'Market Overview',
    subtitle: 'Real-time market indices and sentiment',
    error: 'Error',
    marketSentiment: 'Market Sentiment',
    vixLevel: 'VIX Level',
    positionSizing: 'Position Sizing',
    noData: 'No market data available.',
  },
};
