import { describe, expect, it } from 'vitest';
import { getMessage } from '@/i18n/get-message';

describe('getMessage', () => {
  it('returns Chinese common labels by default and preserves English abbreviations', () => {
    expect(getMessage('zh-CN', 'common.watchlist')).toBe('自选列表');
    expect(getMessage('zh-CN', 'common.navigation')).toBe('导航');
    expect(getMessage('zh-CN', 'common.dashboard')).toBe('仪表盘');
    expect(getMessage('zh-CN', 'common.analyze')).toBe('运行分析');
    expect(getMessage('zh-CN', 'common.gex')).toBe('GEX');
  });

  it('returns English labels when locale is en', () => {
    expect(getMessage('en', 'common.watchlist')).toBe('Watchlist');
    expect(getMessage('en', 'common.navigation')).toBe('Navigation');
    expect(getMessage('en', 'common.dashboard')).toBe('Dashboard');
    expect(getMessage('en', 'common.analyze')).toBe('Run Analysis');
  });

  it('returns Chinese interaction labels while preserving trading abbreviations', () => {
    expect(getMessage('zh-CN', 'interaction.searching')).toBe('搜索中...');
    expect(getMessage('zh-CN', 'interaction.healthOverview')).toBe('健康概览');
    expect(getMessage('zh-CN', 'interaction.vol')).toBe('成交量');
    expect(getMessage('zh-CN', 'interaction.rsi')).toBe('RSI');
    expect(getMessage('zh-CN', 'interaction.smaRsiCombo')).toBe('SMA + RSI 组合');
    expect(getMessage('zh-CN', 'interaction.leapsCall')).toBe('LEAPS Call');
  });

  it('returns Chinese status and trend labels for high-frequency UI copy', () => {
    expect(getMessage('zh-CN', 'interaction.loadingSystemStatus')).toBe('加载系统状态中...');
    expect(getMessage('zh-CN', 'interaction.failedToLoadSystemStatus')).toBe('加载系统状态失败');
    expect(getMessage('zh-CN', 'interaction.allSystemsOperational')).toBe('系统运行正常');
    expect(getMessage('zh-CN', 'interaction.issuesDetected')).toBe('检测到异常');
    expect(getMessage('zh-CN', 'interaction.done')).toBe('已完成');
    expect(getMessage('zh-CN', 'interaction.pending')).toBe('待执行');
    expect(getMessage('zh-CN', 'interaction.bearish')).toBe('看跌');
    expect(getMessage('zh-CN', 'interaction.neutral')).toBe('中性');
    expect(getMessage('zh-CN', 'interaction.bullish')).toBe('看涨');
  });

  it('returns Chinese memory and backtest interaction labels', () => {
    expect(getMessage('zh-CN', 'interaction.loadingMemory')).toBe('加载记忆中...');
    expect(getMessage('zh-CN', 'interaction.analysisResults')).toBe('分析结果');
    expect(getMessage('zh-CN', 'interaction.marketNotes')).toBe('市场笔记');
    expect(getMessage('zh-CN', 'interaction.tradingActions')).toBe('交易动作');
    expect(getMessage('zh-CN', 'interaction.embeddingDim')).toBe('Embedding 维度');
    expect(getMessage('zh-CN', 'interaction.semanticSearch')).toBe('语义搜索');
    expect(getMessage('zh-CN', 'interaction.searchAnalysisResults')).toBe('搜索分析结果...');
    expect(getMessage('zh-CN', 'interaction.noResultsFound')).toBe('未找到结果。');
    expect(getMessage('zh-CN', 'interaction.noMarketNotesYet')).toBe('暂无市场笔记。');
    expect(getMessage('zh-CN', 'interaction.general')).toBe('通用');
    expect(getMessage('zh-CN', 'interaction.backtestFailed')).toBe('回测失败');
    expect(getMessage('zh-CN', 'interaction.configuration')).toBe('配置');
    expect(getMessage('zh-CN', 'interaction.strategy')).toBe('策略');
    expect(getMessage('zh-CN', 'interaction.signalType')).toBe('信号类型');
    expect(getMessage('zh-CN', 'interaction.startDate')).toBe('开始日期');
    expect(getMessage('zh-CN', 'interaction.endDate')).toBe('结束日期');
    expect(getMessage('zh-CN', 'interaction.running')).toBe('运行中...');
    expect(getMessage('zh-CN', 'interaction.runBacktest')).toBe('运行回测');
    expect(getMessage('zh-CN', 'interaction.totalReturn')).toBe('总收益');
    expect(getMessage('zh-CN', 'interaction.annualized')).toBe('年化收益');
    expect(getMessage('zh-CN', 'interaction.winRate')).toBe('胜率');
    expect(getMessage('zh-CN', 'interaction.profitFactor')).toBe('盈亏比');
    expect(getMessage('zh-CN', 'interaction.maxDrawdown')).toBe('最大回撤');
    expect(getMessage('zh-CN', 'interaction.sharpeRatio')).toBe('夏普比率');
    expect(getMessage('zh-CN', 'interaction.equityCurve')).toBe('净值曲线');
    expect(getMessage('zh-CN', 'interaction.monthlyReturns')).toBe('月度收益');
    expect(getMessage('zh-CN', 'interaction.tradeStatistics')).toBe('交易统计');
    expect(getMessage('zh-CN', 'interaction.tradeHistory')).toBe('交易历史');
    expect(getMessage('zh-CN', 'interaction.totalTrades')).toBe('总交易数');
    expect(getMessage('zh-CN', 'interaction.winningTrades')).toBe('盈利交易');
    expect(getMessage('zh-CN', 'interaction.losingTrades')).toBe('亏损交易');
    expect(getMessage('zh-CN', 'interaction.averageWin')).toBe('平均盈利');
    expect(getMessage('zh-CN', 'interaction.averageLoss')).toBe('平均亏损');
    expect(getMessage('zh-CN', 'interaction.bestTrade')).toBe('最佳交易');
    expect(getMessage('zh-CN', 'interaction.worstTrade')).toBe('最差交易');
    expect(getMessage('zh-CN', 'interaction.date')).toBe('日期');
    expect(getMessage('zh-CN', 'interaction.price')).toBe('价格');
    expect(getMessage('zh-CN', 'interaction.return')).toBe('回报');
    expect(getMessage('zh-CN', 'interaction.showingTrades')).toBe('显示前 {shown} / {total} 笔交易');
  });
});
